# core/services/ofx_import_service.py
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from ofxparse import OfxParser

from ..models import Lancamento, get_default_other_category
from ..utils import gerar_hash_lancamento
from .. import services

def processar_arquivo_ofx(ofx_file, conta_selecionada):
    """
    Processa um arquivo OFX de extrato bancário.
    """
    lancamentos_a_revisar = []
    warnings = []
    lancamentos_antigos = [] 
    
    try:
        # ofxparse expects a file-like object
        ofx = OfxParser.parse(ofx_file)
    except Exception as e:
        warnings.append(f"Erro ao parsear o arquivo OFX: {e}")
        return [], warnings

    # Assuming the OFX file contains bank statements
    if not ofx.accounts:
        warnings.append("Nenhuma conta bancária encontrada no arquivo OFX.")
        return [], warnings

    # For simplicity, let's assume we take the first bank account found in the OFX.
    # In a real application, you might want to match it with `conta_selecionada`
    # based on account number, bank ID, etc.
    ofx_account = ofx.accounts[0]

    # Get existing hashes for the selected account to detect duplicates
    hashes_existentes = set(Lancamento.objects.filter(
        conta_bancaria=conta_selecionada,
        import_hash__isnull=False
    ).values_list('import_hash', flat=True))

    # Pega a data de saldo inicial da conta uma vez antes do loop
    data_saldo_inicial_conta = conta_selecionada.data_saldo_inicial

    for transaction in ofx_account.statement.transactions:
        try:
            data_caixa_obj = transaction.date
            valor = Decimal(str(transaction.amount)) # Convert to string first to avoid float precision issues
            
            descricao = transaction.memo.strip() if transaction.memo else transaction.payee.strip() if transaction.payee else "Lançamento OFX"
            
            fitid = transaction.id
            numero_documento = transaction.checknum if transaction.checknum else transaction.refnum if transaction.refnum else fitid

            tipo = 'Crédito' if valor >= 0 else 'Débito'
            data_competencia_obj = data_caixa_obj # For OFX, posted date is usually the competence date

            hash_gerado = gerar_hash_lancamento(
                conta_id=conta_selecionada.id, data_caixa=data_caixa_obj.date(), # Ensure it's a date object
                numero_documento=numero_documento, valor=valor
            )

            # Cria uma instância temporária para aplicar as regras de categoria
            temp_lancamento = Lancamento(
                usuario=conta_selecionada.usuario,
                descricao=descricao,
                categoria=get_default_other_category()
            )
            services.aplicar_regras_para_lancamento(temp_lancamento)

            if data_caixa_obj.date() < data_saldo_inicial_conta:
                # Se for, adiciona à lista de 'antigos' e pula para a próxima linha.
                lancamentos_antigos.append({
                    'data_caixa': data_caixa_obj.date().strftime('%d/%m/%Y'),
                    'descricao': descricao,
                    'valor': valor,
                })
                continue

            lancamentos_a_revisar.append({
                'data_competencia': data_competencia_obj.date().isoformat(), 'data_caixa': data_caixa_obj.date().isoformat(),
                'descricao': descricao, 'valor': f'{abs(valor):.2f}', 'tipo': tipo,
                'import_hash': hash_gerado, 'ja_importado': hash_gerado in hashes_existentes,
                'numero_documento': numero_documento,
                'categoria_id': temp_lancamento.categoria.id,
                'categoria_nome': temp_lancamento.categoria.nome,
            })

        except (InvalidOperation, ValueError, AttributeError) as e:
            warnings.append(f"Erro ao processar transação (FITID: {getattr(transaction, 'id', 'N/A')}): {e}")
            continue

    return lancamentos_a_revisar, warnings, lancamentos_antigos