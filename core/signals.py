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
    print("SINAL ATIVO")
    conta = instance.conta_bancaria

    if conta:
        # Usamos aggregate para calcular a soma de créditos e débitos de uma só vez
        agregado = Lancamento.objects.filter(
            conta_bancaria=conta
        ).aggregate(
            total_creditos=Sum('valor', filter=Q(tipo='C')),
            total_debitos=Sum('valor', filter=Q(tipo='D'))
        )

        creditos = agregado.get('total_creditos') or Decimal(0)
        debitos = agregado.get('total_debitos') or Decimal(0)
        saldo_inicial = conta.saldo_inicial

        novo_saldo = saldo_inicial + creditos - debitos

        # Atualiza o saldo na conta usando .update() para eficiência,
        # evitando chamar o .save() do modelo e re-disparar sinais.
        ContaBancaria.objects.filter(pk=conta.pk).update(saldo_calculado=novo_saldo)

@receiver(post_save, sender=ContaBancaria)
def atualizar_saldo_conta_por_alteracao_conta(sender, instance, **kwargs):
    """
    Acionado sempre que uma ContaBancaria é salva.
    Isso lida com a mudança do saldo_inicial ou da data_saldo_inicial.
    """
    # A lógica é simples: apenas chama nossa função de serviço centralizada.
    recalcular_saldo_conta(instance)