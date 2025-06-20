Excelente ponto! Sua preocupação com a performance do contexto é extremamente pertinente e mostra um entendimento avançado de como interagir eficientemente com modelos de linguagem. Manter um contexto longo e detalhado sobrecarrega a "memória de trabalho" do agente e pode, de fato, degradar a performance e a relevância das respostas.

A estratégia que você busca é criar um **"Ponto de Sincronização"** ou um **"Resumo de Estado Executivo"**. Este documento serve como um ponto de partida autocontido para uma nova sessão com um novo agente (ou comigo mesmo em uma nova conversa), garantindo que ele tenha todo o conhecimento essencial sem precisar reprocessar todo o histórico de desenvolvimento.

Este resumo é diferente da documentação, que é voltada para humanos. Ele é otimizado para ser consumido por uma IA.

---

### **Estratégia: O "Prompt de Sincronização"**

O objetivo é criar um único prompt que contenha três seções principais:

1.  **Contexto Geral e Arquitetura:** O que é o projeto e como ele é construído.
2.  **Estado Atual dos Artefatos de Código:** O código-fonte dos arquivos mais importantes (`models.py`, `views.py`, `urls.py`, `forms.py`) que definem o estado atual da aplicação.
3.  **Roadmap e Próximo Passo Imediato:** Onde paramos e qual é a próxima tarefa a ser executada.

---

### **Geração do Seu Prompt de Sincronização**

Aqui está o prompt completo que você pode copiar e colar para iniciar uma nova sessão com um novo agente.

**(Copie tudo a partir daqui para baixo)**

---

Olá! Sou o Gerente de Produto de um projeto de aplicação web de controle financeiro familiar chamado **"MeuDinDin.io"**, e você é meu especialista em Django e VibeCoding. Estamos continuando um projeto já em andamento. Abaixo está o estado atual completo da aplicação para que você possa continuar o desenvolvimento a partir deste ponto.

### **1. Contexto Geral e Arquitetura**

*   **Projeto:** Aplicação web de finanças pessoais.
*   **Framework:** Django 5.2 (Python 3.11).
*   **Frontend:** Tailwind CSS via CDN.
*   **Banco de Dados:** SQLite (desenvolvimento).
*   **Metodologia:** VibeCoding.
*   **Funcionalidades Já Implementadas:**
    *   Autenticação completa de usuários (Registro, Login, Logout).
    *   CRUDs completos e seguros para `ContaBancaria`, `CartaoCredito` e `Categoria`.
    *   Sistema de categorias Globais (do sistema) e Pessoais (do usuário).
    *   Criação manual de `Lancamentos`.
    *   Importação de extratos CSV com tela de pré-conciliação e prevenção de duplicatas via hash.
    *   Dashboard com gráfico dinâmico (Chart.js) de evolução de saldo.
    *   Tela de extrato por conta com saldo parcial acumulado e interface de ações em massa (seleção por checkbox).
    *   Ações de exclusão em massa e conciliação individual em fila via JavaScript e `request.session`.

### **2. Estado Atual dos Artefatos de Código**

Aqui está o conteúdo dos arquivos principais que definem o estado atual da aplicação.

#### **`core/models.py`**
```python
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q
from decimal import Decimal

class ContaBancaria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contas_bancarias')
    nome_banco = models.CharField(max_length=100, help_text="Ex: Nubank, Itaú, etc.")
    agencia = models.CharField(max_length=20, blank=True, null=True)
    numero_conta = models.CharField(max_length=30)
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    data_saldo_inicial = models.DateField(help_text="Data correspondente ao saldo inicial informado.")

    @property
    def saldo_atual(self):
        soma_creditos = self.lancamentos.filter(tipo='C').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        soma_debitos = self.lancamentos.filter(tipo='D').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        return self.saldo_inicial + soma_creditos - soma_debitos

    def __str__(self):
        return f"{self.nome_banco} ({self.numero_conta})"

class CartaoCredito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cartoes_credito')
    nome_cartao = models.CharField(max_length=100)
    limite = models.DecimalField(max_digits=15, decimal_places=2)
    dia_fechamento = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    dia_vencimento = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    def __str__(self): return self.nome_cartao

class Categoria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias', null=True, blank=True)
    nome = models.CharField(max_length=100)
    class Meta: unique_together = [['usuario', 'nome']]
    def __str__(self): return f"{self.nome} [Sistema]" if not self.usuario else self.nome

class Lancamento(models.Model):
    class TipoTransacao(models.TextChoices): DEBITO = 'D', 'Débito'; CREDITO = 'C', 'Crédito'
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lancamentos')
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data_competencia = models.DateField()
    data_caixa = models.DateField(null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TipoTransacao.choices)
    conciliado = models.BooleanField(default=False)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.CASCADE, null=True, blank=True, related_name='lancamentos')
    cartao_credito = models.ForeignKey(CartaoCredito, on_delete=models.CASCADE, null=True, blank=True, related_name='lancamentos')
    numero_documento = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    import_hash = models.CharField(max_length=32, unique=True, null=True, blank=True, db_index=True, editable=False)
    class Meta: ordering = ['-data_caixa', '-id']
    def __str__(self): return self.descricao

class Orcamento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orcamentos')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    ano_mes = models.DateField()
    class Meta: unique_together = [['usuario', 'categoria', 'ano_mes']]
    def __str__(self): return f"{self.categoria.nome} - {self.ano_mes.strftime('%m/%Y')}"
```

#### **`core/views.py`**
*(Resumido para incluir apenas a lógica principal, omitindo imports repetitivos e CRUDs já padronizados para brevidade).*
```python
# Views Principais
@login_required
def home(request):
    # ... (lógica de cálculo de saldo e dados para o gráfico Chart.js) ...

class LancamentoListView(LoginRequiredMixin, ListView):
    # ... (lógica de queryset com Window Function para calcular saldo parcial) ...

# Views de Autenticação e CRUDs
# SignUpView, LoginView, LogoutView
# CRUDs completos para ContaBancaria, CartaoCredito, Categoria
# Create e Update para Lancamento

# Views de Ações
def conciliar_lancamento_view(request, pk):
    # ... (lógica de conciliação individual e gerenciamento da fila na sessão) ...
    
# Views de Importação
def importar_csv_view(request):
    # ... (lógica da Etapa 1: ler CSV, gerar hash, verificar duplicatas e passar para pré-conciliação via sessão) ...

def confirmar_importacao_view(request):
    # ... (lógica da Etapa 2: ler da sessão, pular ignorados/duplicados e fazer bulk_create) ...

# Views de Ações em Massa
def excluir_lancamentos_em_massa(request):
    # ... (lógica para receber lista de IDs via JSON e deletar) ...

def iniciar_fila_conciliacao_view(request):
    # ... (lógica para receber lista de IDs, salvar na sessão e redirecionar para o primeiro) ...
```

#### **`core/urls.py`**
```python
# Mapeia as URLs para todas as views de CRUD, autenticação, importação e ações em massa.
# Ex:
# path('contas/', ContaBancariaListView.as_view(), name='conta_list')
# path('lancamentos/iniciar-conciliacao/', iniciar_fila_conciliacao_view, name='lancamento_iniciar_conciliacao')
# path('importar/csv/', importar_csv_view, name='importar_csv')
```

#### **Templates e JavaScript**
*   **`base.html`:** Estrutura principal com navegação dinâmica e script de dropdown.
*   **`core/lancamento_list.html`:** Template complexo com barra de ações contextual, checkboxes interativos para seleção em massa.
*   **`static/js/pages/extrato_actions.js`:** Script que gerencia a seleção, atualização da barra de ações e chamadas `fetch` para as views de ações em massa.
*   **`static/js/pages/dashboard_chart.js`:** Script que renderiza o gráfico Chart.js lendo dados de um bloco JSON no template.

### **3. Roadmap e Próximo Passo Imediato**

Paramos na conclusão da Fase 2 do nosso plano de desenvolvimento. A aplicação é funcional e robusta. A próxima fase, **Fase 4: Análise de Dados e Refinamento**, começa agora.

**Próxima Tarefa:**
Com base no nosso roadmap, a próxima funcionalidade a ser implementada é o **Módulo de Orçamento Mensal**.

**Seu Prompt para mim:**
"Crie a interface de gerenciamento de orçamento. O usuário precisa de uma tela onde possa definir, para um determinado mês/ano, um valor máximo para cada uma de suas `Categorias`. Utilize o modelo `Orcamento` que já existe. Crie a view (CRUD completo para Orçamento), o formulário e o template necessários."