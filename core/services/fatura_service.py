# core/services/fatura_service.py
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from ..models import Lancamento, Fatura, CartaoCredito, Categoria


def get_or_create_fatura_aberta(lancamento: Lancamento) -> Fatura:
    """
    Encontra a fatura aberta correta para um lançamento de cartão de crédito
    ou cria uma nova se necessário.
    """
    cartao = lancamento.cartao_credito
    data_compra = lancamento.data_competencia

    # 1. Determina o mês de vencimento da fatura
    mes_vencimento = data_compra.month
    ano_vencimento = data_compra.year

    if data_compra.day > cartao.dia_fechamento:
        # Se a compra foi feita após o fechamento, ela entra na fatura do mês seguinte.
        data_vencimento_fatura = data_compra + relativedelta(months=1)
        mes_vencimento = data_vencimento_fatura.month
        ano_vencimento = data_vencimento_fatura.year

    # 2. Define as datas da fatura
    data_vencimento = date(ano_vencimento, mes_vencimento, cartao.dia_vencimento)
    data_fechamento = data_vencimento - relativedelta(days=(data_vencimento.day - cartao.dia_fechamento))
    
    # O mês de referência é sempre o mês de vencimento
    ano_mes_referencia = date(ano_vencimento, mes_vencimento, 1)

    # 3. Tenta encontrar uma fatura existente ou cria uma nova
    fatura, created = Fatura.objects.get_or_create(
        cartao=cartao,
        usuario=lancamento.usuario,
        ano_mes_referencia=ano_mes_referencia,
        defaults={
            'data_fechamento': data_fechamento,
            'data_vencimento': data_vencimento,
            'status': Fatura.StatusFatura.ABERTA,
        }
    )
    return fatura

def recalcular_valor_fatura(fatura: Fatura):
    """Recalcula o valor total de uma fatura com base em seus lançamentos."""
    if not fatura:
        return

    total = fatura.lancamentos.filter(tipo='D').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
    fatura.valor_total = total
    fatura.save(update_fields=['valor_total'])


@transaction.atomic
def fechar_fatura(fatura: Fatura, data_pagamento: date) -> Lancamento:
    """
    Marca uma fatura como FECHADA e agenda o lançamento de débito correspondente
    na conta de pagamento do cartão para a data de vencimento.
    """
    if fatura.status != Fatura.StatusFatura.ABERTA or fatura.valor_total <= 0:
        return None

    # 1. Obter ou criar a categoria "Pagamento de Fatura"
    # Esta categoria será ignorada nos relatórios de despesas.
    categoria_pagamento, _ = Categoria.objects.get_or_create(
        nome="Pagamento de Fatura",
        usuario__isnull=True
    )

    # 2. Criar o lançamento de débito agendado na conta de pagamento
    lancamento_debito = Lancamento.objects.create(
        usuario=fatura.usuario,
        conta_bancaria=fatura.cartao.conta_pagamento,
        descricao=f"Pagamento Fatura {fatura.cartao.nome_cartao} - Venc. {fatura.data_vencimento.strftime('%d/%m')}",
        valor=fatura.valor_total,
        tipo=Lancamento.TipoTransacao.DEBITO,
        categoria=categoria_pagamento,
        data_competencia=data_pagamento, # Data em que a ação de fechar/pagar foi feita
        data_caixa=fatura.data_vencimento, # Data em que o dinheiro efetivamente sairá da conta
        conciliado=False # Pagamento agora nasce como não conciliado para ser verificado no extrato.
    )

    # 3. Atualizar o status e os valores da fatura
    fatura.status = Fatura.StatusFatura.FECHADA
    fatura.valor_pago = fatura.valor_total
    fatura.lancamento_pagamento = lancamento_debito
    fatura.save()

    # 4. Atualizar a data_caixa de todos os lançamentos da fatura
    # Isso garante que as despesas individuais impactem o fluxo de caixa no mês do pagamento.
    fatura.lancamentos.all().update(data_caixa=fatura.data_vencimento)

    return lancamento_debito

@transaction.atomic
def reabrir_fatura(fatura: Fatura):
    """
    Reabre uma fatura que estava fechada, removendo o lançamento de pagamento agendado.
    """
    if fatura.status != Fatura.StatusFatura.FECHADA:
        return False

    pagamento_agendado = fatura.lancamento_pagamento
    if pagamento_agendado and not pagamento_agendado.conciliado:
        pagamento_agendado.delete()
        fatura.status = Fatura.StatusFatura.ABERTA
        fatura.valor_pago = None
        fatura.lancamento_pagamento = None
        fatura.save()
        return True
    
    return False