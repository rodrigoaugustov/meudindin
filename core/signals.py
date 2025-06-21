from decimal import Decimal
from django.db.models import Sum, Q
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Lancamento, ContaBancaria, get_default_other_category_pk
from .services import recalcular_saldo_conta, aplicar_regras_para_lancamento

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
        return

    if conta:
        recalcular_saldo_conta(conta)

@receiver(post_save, sender=ContaBancaria)
def atualizar_saldo_conta_por_alteracao_conta(sender, instance, **kwargs):
    """
    Acionado sempre que uma ContaBancaria é salva.
    Isso lida com a mudança do saldo_inicial ou da data_saldo_inicial.
    """
    # A lógica é simples: apenas chama nossa função de serviço centralizada.
    recalcular_saldo_conta(instance)