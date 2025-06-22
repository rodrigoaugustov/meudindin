from .models import ContaBancaria, CartaoCredito

def menu_context(request):
    """
    Este context processor disponibiliza a conta de maior saldo para todos os templates.
    """
    # Só executa a lógica se o usuário estiver logado
    if not request.user.is_authenticated:
        return {}

    # Busca a conta bancária do usuário logado com o maior saldo.
    # O '-' antes de 'saldo_calculado' indica ordem decrescente.
    # .first() pega o primeiro resultado ou retorna None se não houver contas.
    conta_maior_saldo = ContaBancaria.objects.filter(
        usuario=request.user
    ).order_by('-saldo_calculado').first()
    
    primeiro_cartao = CartaoCredito.objects.filter(
        usuario=request.user
    ).order_by('nome_cartao').first()

    # Retorna o dicionário que será adicionado ao contexto global
    return {
        'conta_maior_saldo': conta_maior_saldo,
        'primeiro_cartao': primeiro_cartao,
    }