from django.db.models import Sum, Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Lancamento, ContaBancaria

@receiver([post_save, post_delete], sender=Lancamento)
def atualizar_saldo_conta(sender, instance, **kwargs):
    """
    Este sinal é acionado sempre que um Lançamento é salvo ou deletado.
    Ele recalcula e atualiza o campo 'saldo_calculado' da ContaBancaria associada.
    """
    conta = instance.conta_bancaria

    if conta:
        # Usamos aggregate para calcular a soma de créditos e débitos de uma só vez
        agregado = Lancamento.objects.filter(
            conta_bancaria=conta
        ).aggregate(
            total_creditos=Sum('valor', filter=Q(tipo='C')),
            total_debitos=Sum('valor', filter=Q(tipo='D'))
        )

        creditos = agregado.get('total_creditos') or 0.00
        debitos = agregado.get('total_debitos') or 0.00
        saldo_inicial = conta.saldo_inicial

        novo_saldo = saldo_inicial + creditos - debitos

        # Atualiza o saldo na conta usando .update() para eficiência,
        # evitando chamar o .save() do modelo e re-disparar sinais.
        ContaBancaria.objects.filter(pk=conta.pk).update(saldo_calculado=novo_saldo)