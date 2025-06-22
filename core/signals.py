from decimal import Decimal
from django.db.models import Sum, Q
from django.db.models.signals import post_save, post_delete, pre_save
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from .models import Lancamento, ContaBancaria, Fatura, get_default_other_category_pk
from .services import recalcular_saldo_conta, aplicar_regras_para_lancamento, get_or_create_fatura_aberta, recalcular_valor_fatura

@receiver(pre_save, sender=Lancamento)
def categorizar_lancamento_automaticamente(sender, instance, **kwargs):
    """
    Antes de salvar um lançamento, tenta aplicar as regras de categoria.
    Isso acontece para novos lançamentos ou se a categoria for a padrão "Outros",
    permitindo que o usuário "reset" a categoria para re-aplicar as regras.
    """
    # O `instance.pk is None` identifica um novo objeto.
    is_new = instance.pk is None
    is_default_category = instance.categoria_id == get_default_other_category_pk()
    if is_new or is_default_category:
        aplicar_regras_para_lancamento(instance)

    # Se for um lançamento de cartão (novo ou editado), associa a uma fatura
    if instance.cartao_credito:
        fatura = get_or_create_fatura_aberta(instance)
        instance.fatura = fatura

@receiver([post_save, post_delete], sender=Lancamento)
def atualizar_saldo_conta(sender, instance, **kwargs):
    """
    Este sinal é acionado sempre que um Lançamento é salvo ou deletado.
    Ele recalcula e atualiza o campo 'saldo_calculado' da ContaBancaria associada.
    """
    
    # Tenta obter a conta bancária do lançamento.
    # Em uma exclusão em cascata, a conta pode não existir mais.
    try:
        conta = instance.conta_bancaria
    except ContaBancaria.DoesNotExist:
        conta = None

    if conta:
        recalcular_saldo_conta(conta)
    
    # Se o lançamento pertence a uma fatura, recalcula o total da fatura.
    # Precisamos ser defensivos aqui, pois a fatura pode ter sido deletada
    # em cascata junto com o lançamento (ex: ao excluir um cartão de crédito).
    try:
        fatura_para_recalcular = instance.fatura
        if fatura_para_recalcular:
            recalcular_valor_fatura(fatura_para_recalcular)
    except Fatura.DoesNotExist:
        # A fatura foi deletada em cascata. Não há o que fazer.
        pass

@receiver(post_save, sender=ContaBancaria)
def atualizar_saldo_conta_por_alteracao_conta(sender, instance, **kwargs):
    """
    Acionado sempre que uma ContaBancaria é salva.
    Isso lida com a mudança do saldo_inicial ou da data_saldo_inicial.
    """
    # A lógica é simples: apenas chama nossa função de serviço centralizada.
    recalcular_saldo_conta(instance)