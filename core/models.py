# core/models.py

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q, Window, F, Case, When, DecimalField, Max
from django.urls import reverse
from decimal import Decimal

def get_default_other_category():
    """
    Obtém ou cria a categoria 'Outros' do sistema e retorna o objeto.
    Usado para on_delete=models.SET().
    """
    # Usamos get_or_create para garantir que a categoria exista e evitar race conditions.
    # Como é uma categoria de sistema, o usuário é None.
    categoria, created = Categoria.objects.get_or_create(
        nome='Outros',
        usuario__isnull=True,
        defaults={'usuario': None}
    )
    return categoria

def get_default_other_category_pk():
    """Retorna a PK da categoria 'Outros' para o 'default' do campo."""
    return get_default_other_category().pk

# --- Modelos Principais de Cadastros ---

class ContaBancaria(models.Model):
    """Representa uma conta bancária de um usuário."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contas_bancarias')
    nome_banco = models.CharField(max_length=100, help_text="Ex: Nubank, Itaú, etc.")
    agencia = models.CharField(max_length=20, blank=True, null=True)
    numero_conta = models.CharField(max_length=30)
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    data_saldo_inicial = models.DateField(
        help_text="Data correspondente ao saldo inicial informado."
    )
    saldo_calculado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        editable=False,
        help_text="Saldo atual calculado via sinais para otimização de performance."
    )

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
    """Representa uma categoria de despesa ou receita."""
    # MODIFICAÇÃO: Adicione null=True e blank=True
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='categorias',
        null=True,  # Permite que o campo seja nulo no banco de dados
        blank=True  # Permite que o campo seja vazio nos formulários do Django
    )
    nome = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        # A restrição agora precisa considerar que o usuário pode ser nulo.
        unique_together = [['usuario', 'nome']]

    def __str__(self):
        # Adapta o __str__ para mostrar se é uma categoria do sistema
        if self.usuario:
            return f"{self.nome} ({self.usuario.username})"
        return f"{self.nome} [Sistema]"


class RegraCategoria(models.Model):
    """
    Regra para categorizar automaticamente um lançamento baseado em texto na descrição.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='regras_categoria')
    texto_regra = models.CharField(
        max_length=200,
        help_text="Texto a ser procurado na descrição do lançamento (não diferencia maiúsculas/minúsculas)."
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        help_text="Categoria a ser aplicada se o texto for encontrado."
    )
    ordem = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        help_text="Ordem de prioridade da regra (menor número = maior prioridade)."
    )

    class Meta:
        verbose_name = "Regra de Categoria"
        verbose_name_plural = "Regras de Categoria"
        unique_together = [['usuario', 'texto_regra']]
        ordering = ['ordem']

    def __str__(self):
        return f"Se descrição contém '{self.texto_regra}', categorizar como '{self.categoria.nome}'"

    def save(self, *args, **kwargs):
        if not self.pk:
            max_ordem = RegraCategoria.objects.filter(usuario=self.usuario).aggregate(Max('ordem'))['ordem__max']
            self.ordem = (max_ordem or 0) + 1
        super().save(*args, **kwargs)
    

# Métodos em um QuerySet são sempre encadeáveis.
class LancamentoQuerySet(models.QuerySet):
    def com_saldo_parcial(self):
        """
        Anota cada lançamento com o saldo parcial acumulado.
        Este método agora é encadeável em qualquer queryset de Lançamento.
        """
        # 'self' aqui se refere ao queryset em si, por exemplo:
        # o resultado de Lancamento.objects.filter(conta_bancaria=conta)
        return self.annotate(
            valor_com_sinal=Case(
                When(tipo='D', then=-F('valor')),
                default=F('valor'),
                output_field=DecimalField()
            )
        ).annotate(
            saldo_parcial=Window(
                expression=Sum('valor_com_sinal'),
                order_by=[F('data_caixa').asc(), F('id').asc()]
            )
        )

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
    numero_documento = models.CharField(
        max_length=100, 
        null=True, blank=True,
        db_index=True # Ajuda em buscas futuras
    )
    import_hash = models.CharField(
        max_length=32,          # Um hash MD5 tem 32 caracteres
        unique=True,            # Garante a nível de DB que não haja duplicatas
        null=True, blank=True,  # Permite que lançamentos manuais não tenham hash
        db_index=True,          # Essencial para buscas rápidas neste campo
        editable=False          # Este campo não deve ser editado manualmente
    )
    recorrencia_id = models.UUIDField(
        null=True, blank=True, editable=False, db_index=True,
        help_text="ID que agrupa lançamentos de uma mesma recorrência."
    )

    # Relacionamentos (um lançamento pode pertencer a uma categoria, conta ou cartão)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,  # Protege contra a exclusão de categorias em uso
        default=get_default_other_category_pk,
        help_text="Categoria do lançamento."
    )
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.CASCADE, null=True, blank=True, related_name='lancamentos')
    cartao_credito = models.ForeignKey(CartaoCredito, on_delete=models.CASCADE, null=True, blank=True)
    objects = LancamentoQuerySet.as_manager()

    class Meta:
        verbose_name = "Lançamento"
        verbose_name_plural = "Lançamentos"
        ordering = ['-data_competencia', '-id']

    def __str__(self):
        sinal = "-" if self.tipo == self.TipoTransacao.DEBITO else "+"
        return f"{self.data_competencia.strftime('%d/%m/%Y')} - {self.descricao} ({sinal}R$ {self.valor})"

    def get_absolute_url(self):
        if self.conta_bancaria:
            return reverse('core:lancamento_list_atual', kwargs={'conta_pk': self.conta_bancaria.pk})
        # Fallback para lançamentos de cartão de crédito ou outros casos
        return reverse('core:home')


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