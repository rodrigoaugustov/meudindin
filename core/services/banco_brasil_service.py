import requests
from django.conf import settings
from django.core.cache import cache # Usaremos o cache do Django para armazenar o token
from requests.auth import HTTPBasicAuth

from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Q

from ..models import Lancamento, ContaBancaria
from ..utils import gerar_hash_lancamento

# URL para obter o token (do seu print, Fluxo Client Credentials)
TOKEN_URL = 'https://oauth.hm.bb.com.br/oauth/token'

# URL base da API de Extratos (do seu print)
EXTRATO_API_URL = 'https://api.hm.bb.com.br/extratos/v1'


def get_access_token():
    """
    Obtém um token de acesso para a API do BB usando o fluxo Client Credentials.
    Armazena o token em cache para reutilização.
    """
    # 1. Tenta pegar o token do cache
    cached_token = cache.get('bb_api_access_token')
    if cached_token:
        return cached_token

    # 2. Se não está no cache, pede um novo
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    basic = HTTPBasicAuth(settings.BB_CLIENT_ID, settings.BB_CLIENT_SECRET)

    payload = {
        'grant_type': 'client_credentials',
        'scope': 'extrato-info', # Escopo correto para esta API
    }
    
    try:
        response = requests.post(
            TOKEN_URL,
            headers=headers,
            data=payload,
            auth=basic
        )
        response.raise_for_status()
        token_data = response.json()
        
        access_token = token_data['access_token']
        expires_in = token_data['expires_in'] # Tempo em segundos
        
        # 3. Salva o novo token no cache com um tempo de expiração um pouco menor
        #    para garantir que nunca usemos um token expirado.
        cache.set('bb_api_access_token', access_token, timeout=(expires_in - 60))        
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter token do BB: {e}")
        # Em um app real, aqui teríamos um log mais robusto
        return None


def get_extrato(agencia: str, conta: str, data_inicio: str, data_fim: str):
    """
    Busca o extrato de uma conta específica na API do BB.
    """
    access_token = get_access_token()
    if not access_token:
        return None # Falha ao obter o token

    url = f"{EXTRATO_API_URL}/conta-corrente/agencia/{agencia}/conta/{conta}"
    url = f"{EXTRATO_API_URL}/conta-corrente/agencia/551/conta/5087"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'x-br-com-bb-ipa-mciteste': '26968930'
    }
    params = {
        'gw-dev-app-key': settings.BB_GW_DEV_APP_KEY,
        'dataInicioSolicitacao': 21052025, # Formato DDMMAAAA
        'dataFimSolicitacao': 20062025,       # Formato DDMMAAAA
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        print(response.text)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar extrato do BB: {e}")
        return None
    

def mapear_e_salvar_lancamentos(usuario, conta_bancaria, lista_lancamentos_api):
    """
    Recebe a lista de lançamentos da API do BB, mapeia para o modelo Lancamento
    e salva os novos registros no banco de dados, evitando duplicatas.
    """
    # 1. Busca todos os hashes existentes para esta conta para evitar duplicatas
    hashes_existentes = set(Lancamento.objects.filter(
        conta_bancaria=conta_bancaria,
        import_hash__isnull=False
    ).values_list('import_hash', flat=True))

    lancamentos_para_criar = []
    
    for transacao in lista_lancamentos_api:
        # 2. Ignora lançamentos que não são transações reais (como saldos)
        nr_doc = transacao['numeroDocumento']
        if nr_doc==0:
            continue

        # 3. Mapeia os campos da API para os campos do nosso modelo
        try:
            # A data vem como um inteiro (DDMMAAAA), então precisa ser parseada
            data_str = str(transacao['dataLancamento']).zfill(8)
            data_lanc = datetime.strptime(data_str, '%d%m%Y').date()

            valor = Decimal(str(transacao['valorLancamento']))
            
            # O hash será gerado com os dados originais da transação
            hash_gerado = gerar_hash_lancamento(
                conta_id=conta_bancaria.id,
                data_caixa=data_lanc,
                numero_documento=str(transacao['numeroDocumento']),
                valor=valor if transacao['indicadorSinalLancamento'] == 'C' else -valor
            )

            # 4. Se o hash já existe no banco, pula para a próxima transação
            if hash_gerado in hashes_existentes:
                continue

            # 5. Cria a instância do nosso modelo Lancamento, mas não salva ainda
            novo_lancamento = Lancamento(
                usuario=usuario,
                conta_bancaria=conta_bancaria,
                descricao=transacao['textoDescricaoHistorico'],
                valor=valor,
                # O tipo é 'C' para Crédito ou 'D' para Débito
                tipo=transacao['indicadorSinalLancamento'],
                # Usamos a mesma data para competência e caixa, pois a API não diferencia
                data_competencia=data_lanc,
                data_caixa=data_lanc,
                # Lançamentos importados via API já vêm conciliados
                conciliado=True,
                numero_documento=str(transacao['numeroDocumento']),
                import_hash=hash_gerado,
            )
            lancamentos_para_criar.append(novo_lancamento)
            # Adiciona o novo hash ao nosso set para evitar duplicatas dentro do mesmo lote
            hashes_existentes.add(hash_gerado)

        except (KeyError, ValueError) as e:
            # Ignora transações malformadas e imprime um aviso no console
            print(f"Aviso: Ignorando lançamento por erro de parsing. Dados: {transacao}. Erro: {e}")
            continue

    # 6. Salva todos os novos lançamentos no banco de uma só vez (muito eficiente)
    if lancamentos_para_criar:
        Lancamento.objects.bulk_create(lancamentos_para_criar)

        agregado = Lancamento.objects.filter(
            conta_bancaria=conta_bancaria
        ).aggregate(
            total_creditos=Sum('valor', filter=Q(tipo='C')),
            total_debitos=Sum('valor', filter=Q(tipo='D'))
        )
        creditos = agregado.get('total_creditos') or Decimal('0.00')
        debitos = agregado.get('total_debitos') or Decimal('0.00')
        
        novo_saldo = conta_bancaria.saldo_inicial + creditos - debitos
        
        ContaBancaria.objects.filter(pk=conta_bancaria.pk).update(saldo_calculado=novo_saldo)

    # Retorna a quantidade de lançamentos que foram realmente criados
    return len(lancamentos_para_criar)
