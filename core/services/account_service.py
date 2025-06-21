# core/services/account_service.py
from decimal import Decimal
from django.db.models import Sum, Q
from ..models import Lancamento, ContaBancaria

def recalcular_saldo_conta(conta: ContaBancaria):
    """
    Recalcula e atualiza o saldo de uma conta bancária específica.
    Esta é a lógica central que será usada por signals e chamadas manuais.
    """
    if not isinstance(conta, ContaBancaria) or not conta.pk:
        return

    # Agrega todos os lançamentos da conta
    agregado = Lancamento.objects.filter(
        conta_bancaria=conta
    ).aggregate(
        total_creditos=Sum('valor', filter=Q(tipo='C')),
        total_debitos=Sum('valor', filter=Q(tipo='D'))
    )

    creditos = agregado.get('total_creditos') or Decimal(0.00)
    debitos = agregado.get('total_debitos') or Decimal(0.00)
    
    # O cálculo correto sempre parte do saldo inicial da conta
    novo_saldo = conta.saldo_inicial + creditos - debitos

    # Atualiza o campo de forma eficiente, sem disparar outros signals
    ContaBancaria.objects.filter(pk=conta.pk).update(saldo_calculado=novo_saldo)