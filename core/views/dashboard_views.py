# core/views/dashboard_views.py

import json
from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.safestring import mark_safe

from ..models import ContaBancaria, CartaoCredito
from .. import services
from ..templatetags.formatacao import brl

@login_required
def home(request, ano=None, mes=None):
    """
    Renderiza o painel principal (dashboard) com os dados
    financeiros do usuário logado.
    """

    hoje = date.today()
    if ano is None or mes is None:
        ano = hoje.year
        mes = hoje.month

    data_selecionada = date(ano, mes, 1)
    mes_anterior = data_selecionada - relativedelta(months=1)
    mes_seguinte = data_selecionada + relativedelta(months=1)

    contas_bancarias = ContaBancaria.objects.filter(usuario=request.user)
    contas_selecionadas_ids = list(contas_bancarias.values_list('id', flat=True))

    cartoes_de_credito = CartaoCredito.objects.filter(usuario=request.user)
    total_contas = sum(conta.saldo_calculado for conta in contas_bancarias)

    chart_labels, chart_data = services.gerar_dados_grafico_saldo(request.user, ano=ano, mes=mes, contas_ids=contas_selecionadas_ids)
    dados_grafico_despesas = services.gerar_dados_grafico_categorias(request.user, ano=ano, mes=mes, contas_ids=contas_selecionadas_ids)
    dados_fluxo_caixa_completo = services.gerar_dados_fluxo_caixa(request.user, ano, contas_ids=contas_selecionadas_ids)

    # Encontra o índice de "hoje" nos labels do gráfico para dividir a linha em real vs. projetado
    today_str = hoje.strftime('%d/%m')
    chart_today_index = -1
    if today_str in chart_labels:
        chart_today_index = chart_labels.index(today_str)

    context = {
        'contas_bancarias': contas_bancarias,
        'contas_selecionadas_ids': contas_selecionadas_ids,
        'cartoes_de_credito': cartoes_de_credito,
        'total_contas': total_contas,
        'chart_labels': mark_safe(json.dumps(chart_labels)),
        'chart_data': mark_safe(json.dumps(chart_data)),
        'dados_grafico_despesas_json': mark_safe(json.dumps(dados_grafico_despesas)),
        'chart_today_index': chart_today_index,
        'dados_fluxo_caixa': dados_fluxo_caixa_completo['dados_tabela'],
        'data_selecionada': data_selecionada,
        'mes_anterior': mes_anterior, 'mes_seguinte': mes_seguinte,
    }
    
    return render(request, 'core/index.html', context)

@require_POST
@login_required
def dashboard_data_view(request):
    hoje = date.today()
    try:
        data = json.loads(request.body)
        ano = int(data.get('ano'))
        mes = int(data.get('mes'))
        contas_ids = data.get('contas_ids', [])
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Dados inválidos.'}, status=400)

    contas_selecionadas = ContaBancaria.objects.filter(usuario=request.user, pk__in=contas_ids)
    total_contas = sum(c.saldo_calculado for c in contas_selecionadas)

    chart_labels, chart_data = services.gerar_dados_grafico_saldo(request.user, ano=ano, mes=mes, contas_ids=contas_ids)
    dados_grafico_despesas = services.gerar_dados_grafico_categorias(request.user, ano=ano, mes=mes, contas_ids=contas_ids)
    dados_fluxo_caixa_completo = services.gerar_dados_fluxo_caixa(request.user, ano, contas_ids=contas_ids)

    today_str = hoje.strftime('%d/%m')
    chart_today_index = -1
    if today_str in chart_labels:
        chart_today_index = chart_labels.index(today_str)

    dados_fluxo_caixa_formatado = [
        {'mes': item['mes'].strftime('%b').capitalize() + '.', 'total_creditos': brl(item['total_creditos']), 'total_debitos': brl(item['total_debitos'])}
        for item in dados_fluxo_caixa_completo['dados_tabela']
    ]

    response_data = {
        'status': 'success',
        'total_contas': brl(total_contas),
        'saldo_chart': {'labels': chart_labels, 'points': chart_data, 'todayIndex': chart_today_index},
        'despesas_chart': dados_grafico_despesas,
        'fluxo_caixa_tabela': dados_fluxo_caixa_formatado,
    }
    return JsonResponse(response_data)