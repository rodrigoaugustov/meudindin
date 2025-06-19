# core/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# --- Modelos Principais de Cadastros ---

class ContaBancaria(models.Model):
    """Representa uma conta bancária de um usuário."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contas_bancarias')
    nome_banco = models.CharField(max_length=100, help_text="Ex: Nubank, Itaú, etc.")
    agencia = models.CharField(max_length=20, blank=True, null=True)
    numero_conta = models.CharField(max_length=30)
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Conta Bancária"
        verbose_name_plural = "Contas Bancárias"
        unique_together = [['usuario', 'agencia', 'numero_conta']]

    def __str__(self):
        return f"{self.nome_banco} ({self.numero_conta}) - {self.usuario.username}"


class CartaoCredito(models.Model):
    """Representa um cartão de crédito de um usuário."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cartoes_credito')
    nome_cartao = models.CharField(max_length=100, help_text="Ex: Inter Black, C6 Carbon, etc.")
    limite = models.DecimalField(max_digits=15, decimal_places=2)
    dia_fechamento = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Dia do mês em que a fatura fecha."
    )
    dia_vencimento = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Dia do mês para pagamento da fatura."
    )

    class Meta:
        verbose_name = "Cartão de Crédito"
        verbose_name_plural = "Cartões de Crédito"

    def __str__(self):
        return f"{self.nome_cartao} - {self.usuario.username}"


class Categoria(models.Model):
    """Representa uma categoria de despesa ou receita do usuário."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias')
    nome = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        # Garante que um usuário não pode ter duas categorias com o mesmo nome.
        unique_together = [['usuario', 'nome']]

    def __str__(self):
        return f"{self.nome} ({self.usuario.username})"


# --- Modelo Central de Transações ---

class Lancamento(models.Model):
    """Representa uma transação financeira (entrada ou saída)."""

    class TipoTransacao(models.TextChoices):
        DEBITO = 'D', 'Débito'
        CREDITO = 'C', 'Crédito'

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lancamentos')
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data_competencia = models.DateField(help_text="A data em que a compra/transação ocorreu.")
    data_caixa = models.DateField(
        null=True, blank=True,
        help_text="A data em que o dinheiro saiu/entrou efetivamente (pagamento da fatura, débito em conta)."
    )
    tipo = models.CharField(max_length=1, choices=TipoTransacao.choices)
    conciliado = models.BooleanField(default=False, help_text="Marca se o lançamento já foi verificado.")

    # Relacionamentos (um lançamento pode pertencer a uma categoria, conta ou cartão)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.CASCADE, null=True, blank=True)
    cartao_credito = models.ForeignKey(CartaoCredito, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "Lançamento"
        verbose_name_plural = "Lançamentos"
        ordering = ['-data_competencia', '-id']

    def __str__(self):
        sinal = "-" if self.tipo == self.TipoTransacao.DEBITO else "+"
        return f"{self.data_competencia.strftime('%d/%m/%Y')} - {self.descricao} ({sinal}R$ {self.valor})"


# --- Modelo de Planejamento ---

class Orcamento(models.Model):
    """Representa o valor orçado para uma categoria em um determinado mês/ano."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orcamentos')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=15, decimal_places=2, help_text="Valor orçado para o mês.")
    ano_mes = models.DateField(help_text="Primeiro dia do mês e ano para este orçamento. Ex: 01/07/2025")

    class Meta:
        verbose_name = "Orçamento"
        verbose_name_plural = "Orçamentos"
        # Garante que um usuário só pode ter um orçamento por categoria por mês/ano.
        unique_together = [['usuario', 'categoria', 'ano_mes']]

    def __str__(self):
        return f"{self.categoria.nome} - {self.ano_mes.strftime('%m/%Y')} - R$ {self.valor}"