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
    importar_csv_view,
    confirmar_importacao_view,
    conciliar_lancamento_view,
    excluir_lancamentos_em_massa,
    iniciar_fila_conciliacao_view,
    iniciar_fila_edicao_view,
    sincronizar_extrato_bb_view
)

app_name = 'core'

urlpatterns = [
    # Rotas da Aplicação
    path('', views.home, name='home'),

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
    # Rota para CRUD de lançamento
    path('lancamentos/adicionar/', LancamentoCreateView.as_view(), name='lancamento_create'),
    path('lancamentos/<int:pk>/editar/', LancamentoUpdateView.as_view(), name='lancamento_update'),
    path('lancamentos/<int:pk>/excluir/', LancamentoDeleteView.as_view(), name='lancamento_delete'),
    path('lancamentos/bulk-delete/', excluir_lancamentos_em_massa, name='lancamento_bulk_delete'),
    # Rota para a lista de lançamentos (extrato) de uma conta
    path('conta/<int:conta_pk>/extrato/', LancamentoListView.as_view(), name='lancamento_list'),
    # Rota para a importação de CSV
    path('importar/csv/', importar_csv_view, name='importar_csv'),
    # Rota para confirmar a importação
    path('importar/confirmar/', confirmar_importacao_view, name='confirmar_importacao'),
    # Rota para conciliar um lançamento
    path('lancamentos/<int:pk>/conciliar/', conciliar_lancamento_view, name='lancamento_conciliar'),
    # Rota para iniciar a fila de conciliação
    path('lancamentos/iniciar-conciliacao/', iniciar_fila_conciliacao_view, name='lancamento_iniciar_conciliacao'),
    path('lancamentos/iniciar-edicao/', iniciar_fila_edicao_view, name='lancamento_iniciar_edicao'),
    path('conta/<int:conta_pk>/sincronizar-bb/', sincronizar_extrato_bb_view, name='sincronizar_extrato_bb'),

]
