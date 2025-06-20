# core/templatetags/formatacao.py

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from decimal import Decimal

register = template.Library()

@register.filter
def brl(value):
    """
    Filtro para formatar um valor como moeda brasileira (BRL).
    - Garante 2 casas decimais.
    - Usa ponto como separador de milhar.
    - Usa vírgula como separador decimal.
    Ex: 1234.5 -> "1.234,50"
    """
    if value is None or value == '':
        return "0,00"

    try:
        # Garante que o valor é um Decimal para precisão
        value = Decimal(value)
    except (TypeError, ValueError):
        return value

    # Formata o número com 2 casas decimais
    valor_formatado = f"{value:.2f}"
    
    # Substitui o ponto decimal por uma vírgula temporariamente
    valor_formatado = valor_formatado.replace('.', ',')
    
    # Adiciona os separadores de milhar (que usam vírgula por padrão)
    # Precisamos de um pequeno truque para usar pontos
    partes = valor_formatado.split(',')
    parte_inteira = intcomma(partes[0].replace('.', '')).replace(',', '.')
    parte_decimal = partes[1]

    return f"{parte_inteira},{parte_decimal}"