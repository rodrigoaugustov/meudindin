# core/services/rule_service.py
from django.db import transaction
from ..models import Lancamento, RegraCategoria

def aplicar_regras_para_lancamento(lancamento: Lancamento):
    """
    Aplica a primeira regra correspondente a um lançamento.
    A busca não diferencia maiúsculas/minúsculas.
    A verificação ocorre apenas se a categoria for a padrão "Outros".
    """
    if not lancamento.usuario:
        return

    # Busca todas as regras do usuário, ordenadas por prioridade
    regras = RegraCategoria.objects.filter(usuario=lancamento.usuario).order_by('ordem')
    
    descricao_lower = lancamento.descricao.lower()

    for regra in regras:
        if regra.texto_regra.lower() in descricao_lower:
            lancamento.categoria = regra.categoria
            # Encontrou a primeira regra, aplicou e parou.
            return

def aplicar_regra_em_massa(regra: RegraCategoria):
    """
    Aplica uma regra específica a todos os lançamentos existentes do usuário
    que correspondem ao texto da regra.
    Retorna o número de lançamentos atualizados.
    """
    lancamentos_para_atualizar = Lancamento.objects.filter(
        usuario=regra.usuario,
        descricao__icontains=regra.texto_regra
    ).exclude(
        categoria=regra.categoria
    )
    
    count = lancamentos_para_atualizar.count()
    if count > 0:
        lancamentos_para_atualizar.update(categoria=regra.categoria)
    
    return count