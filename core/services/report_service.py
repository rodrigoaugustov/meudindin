# core/services/report_service.py
from datetime import date
import calendar
from decimal import Decimal
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from ..models import Lancamento

def gerar_dados_fluxo_caixa(usuario, ano, contas_ids=None):
    """
    Gera os dados consolidados de fluxo de caixa para um determinado ano.
    Retorna um dicionário com dados para a tabela e para o gráfico.
    Pode ser filtrado por uma lista de IDs de contas.
    """
    # Filtra lançamentos do usuário para o ano especificado que tenham data de caixa
    # e que estejam associados a uma conta bancária (exclui faturas de cartão não pagas)
    lancamentos_ano = Lancamento.objects.filter(
        usuario=usuario,
        data_caixa__year=ano,
        conta_bancaria__isnull=False
    )
    if contas_ids is not None:
        lancamentos_ano = lancamentos_ano.filter(conta_bancaria_id__in=contas_ids)

    # Agrupa por mês e calcula a soma de créditos e débitos
    fluxo_por_mes_query = lancamentos_ano.annotate(
        mes=TruncMonth('data_caixa')
    ).values(
        'mes'
    ).annotate(
        total_creditos=Sum('valor', filter=Q(tipo='C'), default=Decimal(0)),
        total_debitos=Sum('valor', filter=Q(tipo='D'), default=Decimal(0))
    ).order_by('mes')

    # Mapeia os resultados da query para um dicionário para fácil acesso
    fluxo_map = {item['mes'].month: item for item in fluxo_por_mes_query}

    dados_tabela = []
    dados_grafico = {
        'labels': [],
        'data_creditos': [],
        'data_debitos': [],
        'data_saldo': [],
    }

    # Itera por todos os 12 meses do ano para garantir que o gráfico e a tabela estejam completos
    for mes_num in range(1, 13):
        mes_atual = date(ano, mes_num, 1)
        
        nome_mes_abreviado = calendar.month_abbr[mes_num].capitalize()
        dados_grafico['labels'].append(nome_mes_abreviado)

        if mes_num in fluxo_map:
            item = fluxo_map[mes_num]
            total_creditos = item['total_creditos']
            total_debitos = item['total_debitos']
            saldo_mes = total_creditos - total_debitos
            
            # Adiciona dados para a tabela (apenas para meses com movimento)
            dados_tabela.append({
                'mes': mes_atual,
                'total_creditos': total_creditos,
                'total_debitos': total_debitos,
                'saldo_mes': saldo_mes,
            })
        else:
            total_creditos, total_debitos, saldo_mes = Decimal(0), Decimal(0), Decimal(0)

        dados_grafico['data_creditos'].append(float(total_creditos))
        dados_grafico['data_debitos'].append(float(total_debitos))
        dados_grafico['data_saldo'].append(float(saldo_mes))

    return {'dados_tabela': dados_tabela, 'dados_grafico': dados_grafico}