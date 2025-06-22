# core/urls.py

from django.urls import path
# Importa as views de autenticação nativas do Django
from django.contrib.auth import views as auth_views
from . import views

from .views import (
    ContaBancariaListView,
    ContaBancariaCreateView,
    ContaBancariaUpdateView,
    ContaBancariaDeleteView,
    CartaoCreditoListView,
    CartaoCreditoCreateView,
    CartaoCreditoUpdateView,
    CartaoCreditoDeleteView,
    CategoriaListView,
    CategoriaCreateView,
    CategoriaUpdateView,
    CategoriaDeleteView,
    LancamentoCreateView,
    LancamentoListView,
    LancamentoUpdateView, 
    LancamentoDeleteView,
    confirmar_importacao_view,
    conciliar_lancamento_view,
    excluir_lancamentos_em_massa,
    iniciar_fila_conciliacao_view,
    iniciar_fila_edicao_view,
    importar_unificado_view,
    RegraCategoriaListView,
    RegraCategoriaCreateView,
    RegraCategoriaUpdateView,
    RegraCategoriaDeleteView,
    regra_aplicar_retroativo_view,
    reordenar_regras_view,
    criar_regra_lancamento_view,
)
from .views import (
    FaturaListView, FaturaDetailView, fechar_fatura_view, reabrir_fatura_view
)
from .views import fluxo_caixa_view

app_name = 'core'

urlpatterns = [
    # Rotas da Aplicação
    path('', views.home, name='home'),
    path('dashboard-data/', views.dashboard_data_view, name='dashboard_data'),
    path('<int:ano>/<int:mes>/', views.home, name='home_mes'),

    # Rotas de Autenticação
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    path(
        'login/', 
        auth_views.LoginView.as_view(template_name='registration/login.html'), 
        name='login'
    ),
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

urlpatterns += [
    # Rotas do CRUD de Contas Bancárias
    path('contas/', ContaBancariaListView.as_view(), name='conta_list'),
    path('contas/adicionar/', ContaBancariaCreateView.as_view(), name='conta_create'),
    path('contas/<int:pk>/editar/', ContaBancariaUpdateView.as_view(), name='conta_update'),
    path('contas/<int:pk>/excluir/', ContaBancariaDeleteView.as_view(), name='conta_delete'),
    # Rotas do CRUD de Cartões de Crédito
    path('cartoes/', CartaoCreditoListView.as_view(), name='cartao_list'),
    path('cartoes/adicionar/', CartaoCreditoCreateView.as_view(), name='cartao_create'),
    path('cartoes/<int:pk>/editar/', CartaoCreditoUpdateView.as_view(), name='cartao_update'),
    path('cartoes/<int:pk>/excluir/', CartaoCreditoDeleteView.as_view(), name='cartao_delete'),
    # Rotas do CRUD de Categorias
    path('categorias/', CategoriaListView.as_view(), name='categoria_list'),
    path('categorias/adicionar/', CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<int:pk>/editar/', CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/<int:pk>/excluir/', CategoriaDeleteView.as_view(), name='categoria_delete'),
    # Rotas para Regras de Categoria
    path('regras/', RegraCategoriaListView.as_view(), name='regra_list'),
    path('regras/adicionar/', RegraCategoriaCreateView.as_view(), name='regra_create'),
    path('regras/<int:pk>/editar/', RegraCategoriaUpdateView.as_view(), name='regra_update'),
    path('regras/<int:pk>/excluir/', RegraCategoriaDeleteView.as_view(), name='regra_delete'),
    path('regras/<int:pk>/aplicar-retroativo/', regra_aplicar_retroativo_view, name='regra_aplicar_retroativo'),
    path('regras/reordenar/', reordenar_regras_view, name='regras_reordenar'),
    path('regras/criar-via-lancamento/', criar_regra_lancamento_view, name='regra_criar_modal'),
    # Rota para CRUD de lançamento
    path('lancamentos/adicionar/', LancamentoCreateView.as_view(), name='lancamento_create_generic'),
    path('lancamentos/conta/<int:conta_pk>/adicionar/', LancamentoCreateView.as_view(), name='lancamento_conta_create'),
    path('lancamentos/cartao/<int:cartao_pk>/adicionar/', LancamentoCreateView.as_view(), name='lancamento_cartao_create'),
    path('lancamentos/<int:pk>/editar/', LancamentoUpdateView.as_view(), name='lancamento_update'),
    path('lancamentos/<int:pk>/excluir/', LancamentoDeleteView.as_view(), name='lancamento_delete'),
    path('lancamentos/bulk-delete/', excluir_lancamentos_em_massa, name='lancamento_bulk_delete'),
    # Rota para a importação unificada
    path('importar/unificado/', importar_unificado_view, name='importar_unificado'),
    # Rota para confirmar a importação
    path('importar/confirmar/', confirmar_importacao_view, name='confirmar_importacao'),
    # Rota para conciliar um lançamento
    path('lancamentos/<int:pk>/conciliar/', conciliar_lancamento_view, name='lancamento_conciliar'),
    # Rota para iniciar a fila de conciliação
    path('lancamentos/iniciar-conciliacao/', iniciar_fila_conciliacao_view, name='lancamento_iniciar_conciliacao'),
    path('lancamentos/iniciar-edicao/', iniciar_fila_edicao_view, name='lancamento_iniciar_edicao'),
    # Rota Extratos
    path('conta/<int:conta_pk>/extrato/', LancamentoListView.as_view(), name='lancamento_list_atual'),
    path('conta/<int:conta_pk>/extrato/<int:ano>/<int:mes>/', LancamentoListView.as_view(), name='lancamento_list'),
    
    # Rotas para Faturas de Cartão de Crédito (agora "Cartões")
    path('cartoes/<int:cartao_pk>/faturas/', FaturaListView.as_view(), name='fatura_list_atual'),
    path('cartoes/<int:cartao_pk>/faturas/<int:ano>/<int:mes>/', FaturaListView.as_view(), name='fatura_list'),
    path('faturas/<int:pk>/', FaturaDetailView.as_view(), name='fatura_detail'),
    path('faturas/<int:pk>/fechar/', fechar_fatura_view, name='fatura_fechar'),
    path('faturas/<int:pk>/reabrir/', reabrir_fatura_view, name='fatura_reabrir'),

    # Rotas para Relatórios
    path('relatorios/fluxo-caixa/', fluxo_caixa_view, name='relatorio_fluxo_caixa_atual'),
    path('relatorios/fluxo-caixa/<int:ano>/', fluxo_caixa_view, name='relatorio_fluxo_caixa'),

]
