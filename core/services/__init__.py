# core/services/__init__.py

# Expõe as funções principais de cada módulo de serviço
# para que possam ser importadas de forma limpa, como:
# from core import services
# services.gerar_dados_grafico_saldo(...)

from .dashboard_service import gerar_dados_grafico_saldo
from .csv_import_service import processar_arquivo_csv