# core/views/dashboard_views.py

import json
from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.safestring import mark_safe

from ..models import ContaBancaria, CartaoCredito
from .. import services


@login_required
def home(request, ano=None, mes=None):
    """
    Renderiza o painel principal (dashboard) com os dados
    financeiros do usuário logado.
    """

    if ano is None or mes is None:
        hoje = date.today()
        ano = hoje.year
        mes = hoje.month

    data_selecionada = date(ano, mes, 1)
    mes_anterior = data_selecionada - relativedelta(months=1)
    mes_seguinte = data_selecionada + relativedelta(months=1)

    contas_bancarias = ContaBancaria.objects.filter(usuario=request.user)
    cartoes_de_credito = CartaoCredito.objects.filter(usuario=request.user)
    total_contas = sum(conta.saldo_calculado for conta in contas_bancarias)

    chart_labels, chart_data = services.gerar_dados_grafico_saldo(request.user, ano=ano, mes=mes)
    dados_grafico_despesas = services.gerar_dados_grafico_categorias(request.user, ano=ano, mes=mes)

    context = {
        'contas_bancarias': contas_bancarias,
        'cartoes_de_credito': cartoes_de_credito,
        'total_contas': total_contas,
        'chart_labels': mark_safe(json.dumps(chart_labels)),
        'chart_data': mark_safe(json.dumps(chart_data)),
        'dados_grafico_despesas_json': mark_safe(json.dumps(dados_grafico_despesas)),
        'data_selecionada': data_selecionada,
        'mes_anterior': mes_anterior, 'mes_seguinte': mes_seguinte,
    }
    
    return render(request, 'core/index.html', context)