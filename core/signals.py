from decimal import Decimal
from django.db.models import Sum, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Lancamento, ContaBancaria
from .services import recalcular_saldo_conta

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