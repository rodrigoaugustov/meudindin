# core/urls.py

from django.urls import path
from . import views  # Importa as views da app atual (core)

# O namespace ajuda a evitar conflitos de nomes de URL entre diferentes apps
app_name = 'core'

urlpatterns = [
    # Mapeia a URL raiz da app ('') para a view 'home'
    # O 'name' permite que nos refiramos a esta URL de forma fácil no resto do projeto
    path('', views.home, name='home'),
]