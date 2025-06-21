# core/services/csv_import_service.py
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from ..models import Lancamento, get_default_other_category
from ..utils import gerar_hash_lancamento
from .. import services

def processar_arquivo_csv(csv_file, conta_selecionada):
    """
    Processa um arquivo CSV de extrato bancário.
    """
    try:
        decoded_file = csv_file.read().decode('utf-8')
    except UnicodeDecodeError:
        csv_file.seek(0)
        decoded_file = csv_file.read().decode('latin-1')

    io_string = io.StringIO(decoded_file)
    reader = csv.reader(io_string, delimiter=',')
    next(reader, None)

    hashes_existentes = set(Lancamento.objects.filter(
        conta_bancaria=conta_selecionada, 
        import_hash__isnull=False
    ).values_list('import_hash', flat=True))

    lancamentos_a_revisar = []
    warnings = []
    lancamentos_antigos = [] 
    
    # Pega a data de saldo inicial da conta uma vez antes do loop
    data_saldo_inicial_conta = conta_selecionada.data_saldo_inicial
    
    for row in reader:
        try:
            if not row[4] or row[4].strip() == '0': continue
            
            data_caixa_str = row[0].strip()
            descricao = row[2].strip()
            data_competencia_str = row[3].strip() or data_caixa_str
            numero_documento = row[4].strip()
            valor_str = row[5].strip()
            
            data_competencia_obj = datetime.strptime(data_competencia_str, '%d/%m/%Y').date()
            data_caixa_obj = datetime.strptime(data_caixa_str, '%d/%m/%Y').date()

            valor = Decimal(valor_str)
            hash_gerado = gerar_hash_lancamento(
                conta_id=conta_selecionada.id, data_caixa=data_caixa_obj,
                numero_documento=numero_documento, valor=valor
            )

            # Cria uma instância temporária para aplicar as regras de categoria
            temp_lancamento = Lancamento(
                usuario=conta_selecionada.usuario,
                descricao=descricao,
                # Define a categoria padrão para que as regras possam ser aplicadas
                categoria=get_default_other_category()
            )
            services.aplicar_regras_para_lancamento(temp_lancamento)

            if data_caixa_obj < data_saldo_inicial_conta:
                # Se for, adiciona à lista de 'antigos' e pula para a próxima linha.
                lancamentos_antigos.append({
                    'data_caixa': data_caixa_obj.strftime('%d/%m/%Y'),
                    'descricao': row[2].strip(),
                    'valor': row[5].strip(),
                })
                continue

            lancamentos_a_revisar.append({
                'data_competencia': data_competencia_obj.isoformat(),
                'data_caixa': data_caixa_obj.isoformat(),
                'descricao': descricao, 'valor': f'{abs(valor):.2f}',
                'tipo': 'Crédito' if valor > 0 else 'Débito',
                'import_hash': hash_gerado,
                'ja_importado': hash_gerado in hashes_existentes,
                'numero_documento': numero_documento,
                'categoria_id': temp_lancamento.categoria.id,
                'categoria_nome': temp_lancamento.categoria.nome,
            })

        except (IndexError, ValueError, InvalidOperation) as e:
            warnings.append(f"Linha ignorada: {','.join(row)}. Erro: {e}")
            continue

    return lancamentos_a_revisar, warnings, lancamentos_antigos