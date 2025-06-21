# core/views/report_views.py
import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.safestring import mark_safe
from .. import services

@login_required
def fluxo_caixa_view(request, ano=None):
    """
    Renderiza o relatório de Fluxo de Caixa anual.
    """
    if ano is None:
        ano = date.today().year

    dados_completos = services.gerar_dados_fluxo_caixa(request.user, ano)
    dados_relatorio = dados_completos['dados_tabela']
    dados_grafico = dados_completos['dados_grafico']
    
    # Calcula os totais anuais a partir dos dados da tabela
    total_creditos_ano = sum(item['total_creditos'] for item in dados_relatorio)
    total_debitos_ano = sum(item['total_debitos'] for item in dados_relatorio)
    saldo_anual = total_creditos_ano - total_debitos_ano

    context = {
        'ano_selecionado': ano,
        'ano_anterior': ano - 1,
        'ano_seguinte': ano + 1,
        'dados_relatorio': dados_relatorio,
        'total_creditos_ano': total_creditos_ano,
        'total_debitos_ano': total_debitos_ano,
        'saldo_anual': saldo_anual,
        'dados_grafico_json': mark_safe(json.dumps(dados_grafico)),
    }
    
    return render(request, 'core/relatorio_fluxo_caixa.html', context)