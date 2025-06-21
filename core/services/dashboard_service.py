# core/services/dashboard_service.py
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from ..models import ContaBancaria, Lancamento
from django.db.models import Sum, Q

def gerar_dados_grafico_saldo(usuario, ano, mes):
    """
    Calcula os dados para o gráfico de evolução de saldo para o mês e ano especificados.
    """
    contas_bancarias = ContaBancaria.objects.filter(usuario=usuario)
    chart_labels = []
    chart_data = []

    if not contas_bancarias.exists():
        # Se não houver contas, retorna dados vazios para o gráfico
        return [], []

    # Calcula o saldo inicial consolidado para o início do mês selecionado
    data_inicio_mes = date(ano, mes, 1)
    data_fim_mes = data_inicio_mes + relativedelta(months=1) - relativedelta(days=1)

    saldo_acumulado = Decimal('0.0')
    for conta in contas_bancarias:
        saldo_conta = conta.saldo_inicial
        lancamentos_passados = Lancamento.objects.filter(
            conta_bancaria=conta,
            data_caixa__lt=data_inicio_mes,
            data_caixa__gte=conta.data_saldo_inicial
        ).aggregate(
            soma_creditos=Sum('valor', filter=Q(tipo='C')),
            soma_debitos=Sum('valor', filter=Q(tipo='D'))
        )
        saldo_conta += (lancamentos_passados['soma_creditos'] or Decimal('0.0'))
        saldo_conta -= (lancamentos_passados['soma_debitos'] or Decimal('0.0'))
        saldo_acumulado += saldo_conta

    # Busca os lançamentos que ocorreram no mês selecionado
    lancamentos_periodo = Lancamento.objects.filter(
        usuario=usuario,
        data_caixa__range=(data_inicio_mes, data_fim_mes),
        conta_bancaria__isnull=False
                ).order_by('data_caixa')

    mudancas_diarias = {}
    for lancamento in lancamentos_periodo:
        valor_com_sinal = lancamento.valor if lancamento.tipo == 'C' else -lancamento.valor # Valor negativo para débito
        mudancas_diarias[lancamento.data_caixa] = mudancas_diarias.get(lancamento.data_caixa, Decimal('0.0')) + valor_com_sinal

    # Popula os dados do gráfico dia a dia
    for i in range(1, data_fim_mes.day + 1):
        dia_atual = date(ano, mes, i)
        saldo_acumulado += mudancas_diarias.get(dia_atual, Decimal('0.0'))
        
        chart_labels.append(dia_atual.strftime('%d/%m'))
        chart_data.append(float(saldo_acumulado))

    return chart_labels, chart_data