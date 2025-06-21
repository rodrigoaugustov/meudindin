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

     # 1. Mapeia as contas para seus saldos e datas iniciais.
    contas_map = {
        c.id: {'saldo_inicial': c.saldo_inicial, 'data_saldo_inicial': c.data_saldo_inicial}
        for c in contas_bancarias
    }

    # 2. Busca todos os lançamentos passados para todas as contas em uma única query.
    lancamentos_passados = Lancamento.objects.filter(
        usuario=usuario,
        conta_bancaria_id__in=contas_map.keys(),
        data_caixa__lt=data_inicio_mes
    ).values('conta_bancaria_id', 'tipo', 'valor', 'data_caixa')

    # 3. Processa os saldos em memória (muito mais rápido que N queries no DB).
    # Começa com o saldo inicial de cada conta.
    saldos_por_conta = {conta_id: data['saldo_inicial'] for conta_id, data in contas_map.items()}

    # Adiciona/subtrai os lançamentos passados para cada conta.
    for lanc in lancamentos_passados:
        conta_id = lanc['conta_bancaria_id']
        # Apenas considera transações que ocorreram APÓS a data de saldo inicial da conta.
        if lanc['data_caixa'] >= contas_map[conta_id]['data_saldo_inicial']:
            valor_com_sinal = lanc['valor'] if lanc['tipo'] == 'C' else -lanc['valor']
            saldos_por_conta[conta_id] += valor_com_sinal

    # 4. O saldo acumulado no início do mês é a soma dos saldos calculados de cada conta.
    saldo_acumulado = sum(saldos_por_conta.values())


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