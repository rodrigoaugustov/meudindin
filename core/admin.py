# core/admin.py

from django.contrib import admin
from .models import (
    ContaBancaria,
    CartaoCredito,
    Categoria,
    Lancamento,
    Orcamento,
    RegraCategoria
)

@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    """Admin para o modelo ContaBancaria."""
    list_display = ('nome_banco', 'numero_conta', 'usuario', 'saldo_inicial')
    list_filter = ('usuario', 'nome_banco')
    search_fields = ('nome_banco', 'numero_conta', 'usuario__username')
    list_per_page = 20

@admin.register(CartaoCredito)
class CartaoCreditoAdmin(admin.ModelAdmin):
    """Admin para o modelo CartaoCredito."""
    list_display = ('nome_cartao', 'limite', 'dia_vencimento', 'dia_fechamento', 'usuario')
    list_filter = ('usuario',)
    search_fields = ('nome_cartao', 'usuario__username')
    list_per_page = 20

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Admin para o modelo Categoria."""
    list_display = ('nome', 'usuario')
    list_filter = ('usuario',)
    search_fields = ('nome', 'usuario__username')
    list_per_page = 20

@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    """Admin para o modelo Lancamento."""
    list_display = (
        'descricao',
        'valor',
        'tipo',
        'data_competencia',
        'categoria',
        'conta_bancaria',
        'cartao_credito',
        'conciliado',
        'usuario'
    )
    list_filter = (
        'usuario',
        'tipo',
        'conciliado',
        'data_competencia',
        'categoria',
        'conta_bancaria',
        'cartao_credito'
    )
    search_fields = ('descricao', 'categoria__nome', 'usuario__username')
    date_hierarchy = 'data_competencia'
    list_per_page = 25
    
    # Otimização para carregar os dados relacionados de uma vez, evitando múltiplas queries.
    list_select_related = ('usuario', 'categoria', 'conta_bancaria', 'cartao_credito')

@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    """Admin para o modelo Orcamento."""
    list_display = ('categoria', 'valor', 'ano_mes', 'usuario')
    list_filter = ('usuario', 'ano_mes', 'categoria')
    search_fields = ('categoria__nome', 'usuario__username')
    date_hierarchy = 'ano_mes'
    list_per_page = 20
    list_select_related = ('usuario', 'categoria')

@admin.register(RegraCategoria)
class RegraCategoriaAdmin(admin.ModelAdmin):
    """Admin para o modelo RegraCategoria."""
    list_display = ('texto_regra', 'categoria', 'usuario', 'ordem')
    list_filter = ('usuario', 'categoria')
    search_fields = ('texto_regra', 'usuario__username', 'categoria__nome')
    list_per_page = 20
    list_select_related = ('usuario', 'categoria')