# core/services/lancamento_service.py
from dateutil.relativedelta import relativedelta
import uuid
from ..models import Lancamento
from .. import services

def criar_lancamentos_recorrentes(lancamento_base: Lancamento, periodicidade: str, quantidade: int):
    """
    Cria lançamentos futuros com base em um lançamento original.

    :param lancamento_base: O objeto Lancamento original já salvo.
    :param periodicidade: A frequência da recorrência ('DIARIA', 'SEMANAL', 'MENSAL', 'SEMESTRAL', 'ANUAL').
    :param quantidade: O número total de repetições (incluindo a base).
    """
    if not lancamento_base or not lancamento_base.pk or quantidade <= 1:
        return

    # Garante que a série de recorrência tenha um ID
    if lancamento_base.recorrencia_id is None:
        lancamento_base.recorrencia_id = uuid.uuid4()
        lancamento_base.save(update_fields=['recorrencia_id'])

    faturas_afetadas = set()
    data_competencia_atual = lancamento_base.data_competencia
    data_caixa_atual = lancamento_base.data_caixa

    for i in range(quantidade - 1):
        # Calcula a próxima data
        delta_map = {
            'DIARIA': relativedelta(days=1),
            'SEMANAL': relativedelta(weeks=1),
            'MENSAL': relativedelta(months=1),
            'SEMESTRAL': relativedelta(months=6),
            'ANUAL': relativedelta(years=1),
        }
        delta = delta_map.get(periodicidade, relativedelta(months=1))
        
        data_competencia_atual += delta
        if data_caixa_atual: data_caixa_atual += delta # Garante que data_caixa_atual é um objeto date

        novo_lancamento = Lancamento(
            usuario=lancamento_base.usuario, descricao=lancamento_base.descricao,
            valor=lancamento_base.valor, tipo=lancamento_base.tipo,
            categoria=lancamento_base.categoria, conta_bancaria=lancamento_base.conta_bancaria,
            cartao_credito=lancamento_base.cartao_credito, data_competencia=data_competencia_atual,
            data_caixa=data_caixa_atual, conciliado=False,
            recorrencia_id=lancamento_base.recorrencia_id
        )
        
        # Se for um lançamento de cartão, precisamos associar a fatura correta.
        # Não podemos usar bulk_create aqui, pois ele não dispara os sinais pre_save.
        if novo_lancamento.cartao_credito:
            fatura = services.get_or_create_fatura_aberta(novo_lancamento)
            novo_lancamento.fatura = fatura
            faturas_afetadas.add(fatura)
        
        novo_lancamento.save()

    # Após criar todos os lançamentos, recalcula o valor das faturas afetadas.
    if faturas_afetadas:
        for fatura in faturas_afetadas:
            services.recalcular_valor_fatura(fatura)