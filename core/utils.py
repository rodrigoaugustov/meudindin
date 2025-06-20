# core/utils.py

import hashlib
from decimal import Decimal

def gerar_hash_lancamento(conta_id, data_caixa, numero_documento, valor):
    """
    Gera um hash MD5 único usando os campos mais confiáveis da transação.
    """
    valor_str = f"{Decimal(valor):.2f}"
    
    # Nova string canônica, muito mais robusta
    string_unica = (
        f"conta:{conta_id}-"
        f"data:{data_caixa}-"
        f"doc:{numero_documento.strip()}-"
        f"valor:{valor_str}"
    )
    
    return hashlib.md5(string_unica.encode('utf-8')).hexdigest()