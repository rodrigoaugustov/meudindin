# core/services/dashboard_service.py
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from ..models import ContaBancaria, Lancamento
from django.db.models import Sum, Q

def gerar_dados_grafico_saldo(usuario, ano, mes, contas_ids=None):
    """
    Calcula os dados para o gráfico de evolução de saldo para o mês e ano especificados.
    Pode ser filtrado por uma lista de IDs de contas.
    """
    # 1. Filtra as contas bancárias que serão consideradas no cálculo.
    contas_a_calcular = ContaBancaria.objects.filter(usuario=usuario)
    if contas_ids is not None:
        contas_a_calcular = contas_a_calcular.filter(pk__in=contas_ids)
    
    if not contas_a_calcular.exists():
        return [], []

    # 2. Define o período do gráfico.
    data_inicio_mes = date(ano, mes, 1)
    data_fim_mes = data_inicio_mes + relativedelta(months=1) - relativedelta(days=1)

    # 3. Calcula o saldo consolidado no início do mês para as contas selecionadas.
    saldo_acumulado = Decimal('0.0')
    for conta in contas_a_calcular:
        saldo_da_conta = conta.saldo_inicial
        
        # Soma as transações passadas da conta para encontrar o saldo no início do mês.
        agregado_passado = Lancamento.objects.filter(
            conta_bancaria=conta,
            data_caixa__gte=conta.data_saldo_inicial,
            data_caixa__lt=data_inicio_mes
        ).aggregate(
            creditos=Sum('valor', filter=Q(tipo='C'), default=Decimal('0.0')),
            debitos=Sum('valor', filter=Q(tipo='D'), default=Decimal('0.0'))
        )
        
        saldo_da_conta += (agregado_passado['creditos'] - agregado_passado['debitos'])
        saldo_acumulado += saldo_da_conta

    # 4. Busca os lançamentos do período para as contas selecionadas.
    lancamentos_periodo = Lancamento.objects.filter(
        usuario=usuario,
        data_caixa__range=(data_inicio_mes, data_fim_mes),
        conta_bancaria__in=contas_a_calcular
    ).order_by('data_caixa')

    # 5. Agrupa as mudanças diárias para aplicar ao saldo.
    mudancas_diarias = {}
    for lancamento in lancamentos_periodo:
        valor_com_sinal = lancamento.valor if lancamento.tipo == 'C' else -lancamento.valor
        mudancas_diarias[lancamento.data_caixa] = mudancas_diarias.get(lancamento.data_caixa, Decimal('0.0')) + valor_com_sinal

    # 6. Popula os dados do gráfico dia a dia, começando com o saldo inicial calculado.
    chart_labels = []
    chart_data = []
    for i in range(1, data_fim_mes.day + 1):
        dia_atual = date(ano, mes, i)
        saldo_acumulado += mudancas_diarias.get(dia_atual, Decimal('0.0'))
        
        chart_labels.append(dia_atual.strftime('%d/%m'))
        chart_data.append(float(saldo_acumulado))

    return chart_labels, chart_data

def gerar_dados_grafico_categorias(usuario, ano, mes, contas_ids=None):
    """
    Calcula os dados para o gráfico de rosca de despesas por categoria.
    Limita a 5 categorias principais e agrupa o resto em 'Outros'.
    Pode ser filtrado por uma lista de IDs de contas.
    """
    data_inicio_mes = date(ano, mes, 1)
    data_fim_mes = data_inicio_mes + relativedelta(months=1) - relativedelta(days=1)

    # Busca todas as despesas do período, agrupadas por categoria
    despesas_qs = Lancamento.objects.filter(
        usuario=usuario,
        tipo='D', # Apenas Débitos (despesas)
        data_competencia__range=(data_inicio_mes, data_fim_mes)
    )

    if contas_ids is not None:
        # Ao filtrar por contas, mostramos apenas despesas que saíram diretamente dessas contas.
        # Lançamentos de cartão de crédito são intencionalmente excluídos do gráfico de categorias quando um filtro de conta está ativo,
        # pois eles não estão vinculados a uma conta bancária específica no momento da despesa.
        despesas_qs = despesas_qs.filter(conta_bancaria_id__in=contas_ids)

    despesas_por_categoria = despesas_qs.values(
        'categoria__nome' # Agrupa pelo nome da categoria
    ).annotate(
        total=Sum('valor') # Soma os valores para cada categoria
    ).order_by(
        '-total' # Ordena do maior para o menor gasto
    )

    if not despesas_por_categoria:
        return {}

    # Prepara os dados para a visão completa (todas as categorias)
    labels_completos = [item['categoria__nome'] or 'Sem Categoria' for item in despesas_por_categoria]
    data_completos = [float(item['total']) for item in despesas_por_categoria]

    # Lógica para "Top 5 + Outros"
    TOP_N = 5
    labels_condensados = []
    data_condensados = []

    top_items = despesas_por_categoria[:TOP_N]
    outros_items = despesas_por_categoria[TOP_N:]

    for item in top_items:
        labels_condensados.append(item['categoria__nome'] or 'Sem Categoria')
        data_condensados.append(float(item['total']))

    if outros_items:
        total_outros = sum(item['total'] for item in outros_items)
        labels_condensados.append('Outros')
        data_condensados.append(float(total_outros))

    return {
        'condensado': {'labels': labels_condensados, 'data': data_condensados},
        'completo': {'labels': labels_completos, 'data': data_completos}
    }
