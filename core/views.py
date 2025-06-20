# core/views.py
import json
import csv
import io
from datetime import date, timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Window, F, Case, When, DecimalField, Value
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.views.decorators.http import require_POST

# Importa as views de autenticação que já criamos
from django.urls import reverse_lazy
from django.urls import reverse
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Lancamento, Categoria, ContaBancaria, CartaoCredito
from .forms import ContaBancariaForm, CartaoCreditoForm, CategoriaForm, LancamentoForm, CSVImportForm, ConciliacaoForm
from .utils import gerar_hash_lancamento



@login_required
def home(request):
    """
    Renderiza o painel principal (dashboard) com os dados
    financeiros do usuário logado.
    """
    # Busca os objetos financeiros pertencentes apenas ao usuário da requisição
    contas_bancarias = ContaBancaria.objects.filter(usuario=request.user)
    cartoes_de_credito = CartaoCredito.objects.filter(usuario=request.user)
    total_contas = sum(conta.saldo_atual for conta in contas_bancarias)

    chart_labels = []
    chart_data = []

    if contas_bancarias.exists():
        # 1. Determina o período do gráfico (ex: últimos 30 dias)
        hoje = date.today() + relativedelta(day=31)
        data_inicio_grafico = hoje.replace(day=1)

        # 2. Calcula o saldo total em (data_inicio_grafico - 1 dia)
        #    Este será o nosso ponto de partida.
        saldo_acumulado = 0
        for conta in contas_bancarias:
            # Saldo inicial da conta
            saldo_conta = conta.saldo_inicial
            # Soma/subtrai lançamentos ANTERIORES ao início do gráfico
            lancamentos_passados = Lancamento.objects.filter(
                conta_bancaria=conta,
                data_caixa__lt=data_inicio_grafico,
                data_caixa__gte=conta.data_saldo_inicial
            ).aggregate(
                soma_creditos=Sum('valor', filter=Q(tipo='C')),
                soma_debitos=Sum('valor', filter=Q(tipo='D'))
            )
            saldo_conta += (lancamentos_passados['soma_creditos'] or 0)
            saldo_conta -= (lancamentos_passados['soma_debitos'] or 0)
            saldo_acumulado += saldo_conta
        
        # 3. Pega todos os lançamentos DENTRO do período do gráfico para otimizar
        lancamentos_periodo = Lancamento.objects.filter(
            usuario=request.user,
            data_caixa__range=(data_inicio_grafico, hoje)
        ).order_by('data_caixa')

        # 4. Cria um dicionário com a mudança de saldo por dia
        mudancas_diarias = {}
        for lancamento in lancamentos_periodo:
            valor_com_sinal = lancamento.valor if lancamento.tipo == 'C' else -lancamento.valor
            mudancas_diarias[lancamento.data_caixa] = mudancas_diarias.get(lancamento.data_caixa, 0) + valor_com_sinal

        # 5. Itera dia a dia, do início ao fim do período, e calcula o saldo final de cada dia
        for i in range(30):
            dia_atual = data_inicio_grafico + timedelta(days=i)
            saldo_acumulado += mudancas_diarias.get(dia_atual, 0)
            
            chart_labels.append(dia_atual.strftime('%d/%m'))
            chart_data.append(float(saldo_acumulado)) # Chart.js funciona melhor com float

    context = {
        'contas_bancarias': contas_bancarias,
        'cartoes_de_credito': cartoes_de_credito,
        'total_contas': total_contas,
        # Passa os dados do gráfico para o template como JSON seguro
        'chart_labels': mark_safe(json.dumps(chart_labels)),
        'chart_data': mark_safe(json.dumps(chart_data)),
    }
    return render(request, 'core/index.html', context)


# View de Registro (SignUp)
class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('core:login') 
    template_name = 'registration/signup.html'

# --- CRUD para Contas Bancárias ---

class ContaBancariaListView(LoginRequiredMixin, ListView):
    model = ContaBancaria
    template_name = 'core/conta_bancaria_list.html'
    context_object_name = 'contas' # Nome da variável no template

    def get_queryset(self):
        """Sobrescreve o queryset para retornar apenas as contas do usuário logado."""
        return ContaBancaria.objects.filter(usuario=self.request.user).order_by('nome_banco')

class ContaBancariaCreateView(LoginRequiredMixin, CreateView):
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'core/conta_bancaria_form.html'
    success_url = reverse_lazy('core:conta_list')

    def form_valid(self, form):
        """Sobrescreve para associar a nova conta ao usuário logado."""
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class ContaBancariaUpdateView(LoginRequiredMixin, UpdateView):
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'core/conta_bancaria_form.html'
    success_url = reverse_lazy('core:conta_list')

    def get_queryset(self):
        """Garante que o usuário só pode editar suas próprias contas."""
        return ContaBancaria.objects.filter(usuario=self.request.user)

class ContaBancariaDeleteView(LoginRequiredMixin, DeleteView):
    model = ContaBancaria
    template_name = 'core/conta_bancaria_confirm_delete.html'
    success_url = reverse_lazy('core:conta_list')

    def get_queryset(self):
        """Garante que o usuário só pode excluir suas próprias contas."""
        return ContaBancaria.objects.filter(usuario=self.request.user)
    
# --- CRUD para Cartões de Crédito ---

class CartaoCreditoListView(LoginRequiredMixin, ListView):
    model = CartaoCredito
    template_name = 'core/cartao_credito_list.html'
    context_object_name = 'cartoes'

    def get_queryset(self):
        return CartaoCredito.objects.filter(usuario=self.request.user).order_by('nome_cartao')

class CartaoCreditoCreateView(LoginRequiredMixin, CreateView):
    model = CartaoCredito
    form_class = CartaoCreditoForm
    template_name = 'core/cartao_credito_form.html'
    success_url = reverse_lazy('core:cartao_list')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class CartaoCreditoUpdateView(LoginRequiredMixin, UpdateView):
    model = CartaoCredito
    form_class = CartaoCreditoForm
    template_name = 'core/cartao_credito_form.html'
    success_url = reverse_lazy('core:cartao_list')

    def get_queryset(self):
        return CartaoCredito.objects.filter(usuario=self.request.user)

class CartaoCreditoDeleteView(LoginRequiredMixin, DeleteView):
    model = CartaoCredito
    template_name = 'core/cartao_credito_confirm_delete.html'
    success_url = reverse_lazy('core:cartao_list')

    def get_queryset(self):
        return CartaoCredito.objects.filter(usuario=self.request.user)
    
# --- CRUD para Categorias ---
class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = 'core/categoria_list.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        # Retorna categorias do sistema (usuario=None) OU categorias do usuário logado
        return Categoria.objects.filter(
            Q(usuario=self.request.user) | Q(usuario__isnull=True)
        ).order_by('nome')

class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'core/categoria_form.html'
    success_url = reverse_lazy('core:categoria_list')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'core/categoria_form.html'
    success_url = reverse_lazy('core:categoria_list')

    def get_queryset(self):
        return Categoria.objects.filter(usuario=self.request.user)

class CategoriaDeleteView(LoginRequiredMixin, DeleteView):
    model = Categoria
    template_name = 'core/categoria_confirm_delete.html'
    success_url = reverse_lazy('core:categoria_list')

    def get_queryset(self):
        return Categoria.objects.filter(usuario=self.request.user)
    
class LancamentoCreateView(LoginRequiredMixin, CreateView):
    model = Lancamento
    form_class = LancamentoForm
    template_name = 'core/lancamento_form.html'
    success_url = reverse_lazy('core:home')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Adiciona dados dos cartões ao contexto para uso no JavaScript."""
        context = super().get_context_data(**kwargs)
        cartoes = CartaoCredito.objects.filter(usuario=self.request.user)
        # Cria um dicionário com ID do cartão e seus dias de fechamento/vencimento
        cartoes_data = {
            c.id: {'fechamento': c.dia_fechamento, 'vencimento': c.dia_vencimento}
            for c in cartoes
        }
        # Converte o dicionário para uma string JSON segura para o template
        context['cartoes_data_json'] = mark_safe(json.dumps(cartoes_data))
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

class LancamentoListView(LoginRequiredMixin, ListView):
    model = Lancamento
    template_name = 'core/lancamento_list.html'
    context_object_name = 'lancamentos'
    paginate_by = 50

    def get_queryset(self):
        self.conta = get_object_or_404(
            ContaBancaria, 
            pk=self.kwargs['conta_pk'], 
            usuario=self.request.user
        )

        # 1. Busca os lançamentos e anota o valor com sinal
        queryset = Lancamento.objects.filter(
            conta_bancaria=self.conta
        ).annotate(
            valor_com_sinal=Case(
                When(tipo='D', then=-F('valor')),
                default=F('valor'),
                output_field=DecimalField()
            )
        )

        # 2. Anota o saldo parcial acumulado (cálculo pesado feito pelo DB)
        queryset = queryset.annotate(
            saldo_parcial=Window(
                expression=Sum('valor_com_sinal'),
                order_by=[F('data_caixa').asc(), F('id').asc()]
            )
        )

        # 3. Ordena para exibição correta (mais recente primeiro)
        #    Esta query retorna OBJETOS LANCAMENTO COMPLETOS
        return queryset.order_by('-data_caixa', '-id')

    def get_context_data(self, **kwargs):
        # Pega o contexto padrão (que inclui a lista paginada de 'lancamentos')
        context = super().get_context_data(**kwargs)
        
        # Adiciona a conta ao contexto
        context['conta'] = self.conta

        # --- INÍCIO DA CORREÇÃO DEFINITIVA ---
        # 4. Pós-processamento em Python para calcular o saldo final de cada linha
        #    Isso é feito APÓS a query ao banco, sobre a lista de objetos já na memória.
        #    É rápido e garante que não quebramos a query.
        for lancamento in context['lancamentos']:
            lancamento.saldo_final_linha = self.conta.saldo_inicial + lancamento.saldo_parcial
        # --- FIM DA CORREÇÃO DEFINITIVA ---

        return context
    
class LancamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Lancamento
    form_class = LancamentoForm
    template_name = 'core/lancamento_form.html'
    success_url = reverse_lazy('core:home') # Ou para onde você preferir

    def get_queryset(self):
        """Garante que o usuário só pode editar seus próprios lançamentos."""
        return Lancamento.objects.filter(usuario=self.request.user)

    def get_form_kwargs(self):
        """Passa o usuário para o formulário para filtrar os dropdowns."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        """Redireciona de volta para o extrato da conta do lançamento."""
        return reverse_lazy('core:lancamento_list', kwargs={'conta_pk': self.object.conta_bancaria.pk})


class LancamentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Lancamento
    template_name = 'core/lancamento_confirm_delete.html'
    
    def get_queryset(self):
        """Garante que o usuário só pode excluir seus próprios lançamentos."""
        return Lancamento.objects.filter(usuario=self.request.user)
    
    def get_success_url(self):
        """Redireciona de volta para o extrato da conta após a exclusão."""
        # Precisamos pegar o pk da conta antes que o objeto seja deletado
        self.conta_pk = self.object.conta_bancaria.pk
        return reverse_lazy('core:lancamento_list', kwargs={'conta_pk': self.conta_pk})
    
@require_POST
@login_required
def excluir_lancamentos_em_massa(request):
    try:
        data = json.loads(request.body)
        ids = data.get('ids', [])
        
        # Garante que os IDs são números e que pertencem ao usuário
        lancamentos_a_excluir = Lancamento.objects.filter(
            usuario=request.user, 
            id__in=[int(id) for id in ids]
        )
        
        count = lancamentos_a_excluir.count()
        lancamentos_a_excluir.delete()
        
        return JsonResponse({'status': 'success', 'deleted_count': count})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)

    
@login_required
def importar_csv_view(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            conta_selecionada = form.cleaned_data['conta_bancaria']
            
            try:
                decoded_file = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                csv_file.seek(0)
                decoded_file = csv_file.read().decode('latin-1')

            io_string = io.StringIO(decoded_file)
            reader = csv.reader(io_string, delimiter=',')
            next(reader, None) # Pula cabeçalho
            hashes_existentes = set(Lancamento.objects.filter(
                                                                conta_bancaria=conta_selecionada, 
                                                                import_hash__isnull=False
                                                            ).values_list('import_hash', flat=True))

            lancamentos_a_revisar = []
            for row in reader:
                try:
                    if not row[4] or row[4].strip() == '0':
                        continue
                    
                    data_caixa_str = row[0].strip()
                    descricao = row[2].strip()
                    data_competencia_str = row[3].strip() or data_caixa_str
                    numero_documento = row[4].strip()
                    valor_str = row[5].strip()
                    
                    data_competencia_obj = datetime.strptime(data_competencia_str, '%d/%m/%Y').date()
                    data_competencia_iso = data_competencia_obj.strftime('%Y-%m-%d')

                    data_caixa_obj = datetime.strptime(data_caixa_str, '%d/%m/%Y').date()
                    data_caixa_iso = data_caixa_obj.strftime('%Y-%m-%d')

                    valor = Decimal(valor_str)
                    tipo = 'Crédito' if valor > 0 else 'Débito'
                    valor_absoluto = abs(valor)

                    hash_gerado = gerar_hash_lancamento(
                        conta_id=conta_selecionada.id,
                        data_caixa=data_caixa_iso,
                        numero_documento=numero_documento,
                        valor=valor # Usamos o valor com sinal
                    )

                    # Salva os dados processados em um dicionário simples
                    lancamentos_a_revisar.append({
                        'data_competencia': data_competencia_iso,
                        'data_caixa':data_caixa_iso,
                        'descricao': descricao,
                        'valor': f'{valor_absoluto:.2f}',
                        'tipo': tipo,
                        'import_hash': hash_gerado,
                        'ja_importado': hash_gerado in hashes_existentes, # Verifica se o hash já existe
                        'numero_documento': numero_documento
                    })

                except (IndexError, ValueError, InvalidOperation) as e:
                    messages.warning(request, f"Linha ignorada: {','.join(row)}. Erro: {e}")
                    continue
            
            # Armazena os dados processados e o ID da conta na sessão do usuário
            request.session['lancamentos_para_importar'] = lancamentos_a_revisar
            request.session['conta_pk_para_importar'] = conta_selecionada.pk
            
            # Renderiza o template de pré-conciliação
            return render(request, 'core/pre_conciliacao.html', {'lancamentos': lancamentos_a_revisar, 'conta': conta_selecionada})

    # Se o método for GET, exibe o formulário de upload normal
    form = CSVImportForm(user=request.user)
    return render(request, 'core/importar_csv.html', {'form': form})

@login_required
def confirmar_importacao_view(request):
    if request.method == 'POST':
        lancamentos_data = request.session.pop('lancamentos_para_importar', [])
        conta_pk = request.session.pop('conta_pk_para_importar', None)
        
        # Lê os índices das linhas que o usuário marcou para ignorar
        indices_a_ignorar_str = request.POST.get('indices_a_ignorar', '')
        indices_a_ignorar = {int(i) for i in indices_a_ignorar_str.split(',') if i}

        if not lancamentos_data or not conta_pk:
            messages.error(request, "Nenhum dado para importar encontrado ou a sessão expirou. Por favor, tente novamente.")
            return redirect('core:importar_csv')

        conta = get_object_or_404(ContaBancaria, pk=conta_pk, usuario=request.user)
        
        lancamentos_para_criar = []
        # Itera sobre os dados usando enumerate para ter acesso ao índice
        for indice, data in enumerate(lancamentos_data):
            if indice in indices_a_ignorar or data.get('ja_importado'): # Pula se ignorado OU se já importado
                continue

            lancamentos_para_criar.append(Lancamento(
                usuario=request.user,
            conta_bancaria=conta,
            data_competencia=data['data_competencia'],
            data_caixa=data['data_caixa'],
            descricao=data['descricao'],
            valor=Decimal(data['valor']),
            tipo='C' if data['tipo'] == 'Crédito' else 'D',
            conciliado=True,
            import_hash=data['import_hash'],
            numero_documento=data['numero_documento'] # <-- SALVA O NÚMERO DO DOCUMENTO
            ))

        if lancamentos_para_criar:
            Lancamento.objects.bulk_create(lancamentos_para_criar)
            messages.success(request, f"{len(lancamentos_para_criar)} lançamentos foram importados com sucesso!")
        else:
            messages.warning(request, "Nenhum lançamento foi importado.")
            
        return redirect('core:lancamento_list', conta_pk=conta.pk)

    return redirect('core:importar_csv')


@login_required
def conciliar_lancamento_view(request, pk):
    lancamento = get_object_or_404(Lancamento, pk=pk, usuario=request.user)

    if request.method == 'POST':
        form = ConciliacaoForm(request.POST)
        if form.is_valid():
            lancamento.data_caixa = form.cleaned_data['data_caixa']
            lancamento.valor = form.cleaned_data['valor']
            lancamento.conciliado = True
            lancamento.save()
            messages.success(request, "Lançamento conciliado com sucesso!")
            queue = request.session.get('conciliation_queue', [])

            # Remove o item que acabamos de processar
            if pk in queue:
                queue.remove(pk)
                
            if queue:
                next_id = queue[0]
                request.session['conciliation_queue'] = queue # Salva a fila atualizada
                # ...redireciona para o próximo item
                return redirect('core:lancamento_conciliar', pk=next_id)
            else:
                # Se a fila acabou, limpa a chave da sessão e volta para o extrato
                request.session.pop('conciliation_queue', None)
                return redirect('core:lancamento_list', conta_pk=lancamento.conta_bancaria.pk)
    else:
        # Preenche o formulário com os dados existentes
        form = ConciliacaoForm(initial={
            'data_caixa': lancamento.data_caixa.strftime('%Y-%m-%d'),
            'valor': lancamento.valor
        })

    context = {
        'form': form,
        'lancamento': lancamento
    }
    return render(request, 'core/conciliar_lancamento.html', context)

@require_POST
@login_required
def iniciar_fila_conciliacao_view(request):
    try:
        data = json.loads(request.body)
        ids = [int(id_str) for id_str in data.get('ids', [])]

        # Validação: Garante que todos os IDs pertencem ao usuário
        lancamentos_validos = Lancamento.objects.filter(usuario=request.user, id__in=ids)
        ids_validos = list(lancamentos_validos.values_list('id', flat=True))

        if not ids_validos:
            return JsonResponse({'status': 'error', 'message': 'Nenhum lançamento válido selecionado.'}, status=400)

        # Salva a fila de IDs válidos na sessão
        request.session['conciliation_queue'] = ids_validos
        
        # Pega o primeiro ID para iniciar o fluxo
        primeiro_id = ids_validos[0]
        
        # Gera a URL de redirecionamento para o primeiro item
        redirect_url = reverse('core:lancamento_conciliar', kwargs={'pk': primeiro_id})
        
        return JsonResponse({'status': 'success', 'redirect_url': redirect_url})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)