# core/services/__init__.py

# Expõe as funções principais de cada módulo de serviço
# para que possam ser importadas de forma limpa, como:
# from core import services
# services.gerar_dados_grafico_saldo(...)

from .dashboard_service import gerar_dados_grafico_saldo, gerar_dados_grafico_categorias
from .csv_import_service import processar_arquivo_csv
from .ofx_import_service import processar_arquivo_ofx # New import
from .account_service import recalcular_saldo_conta
from .rule_service import aplicar_regras_para_lancamento, aplicar_regra_em_massa
from .report_service import gerar_dados_fluxo_caixa
