# core/views.py
import json

from datetime import date
from dateutil.relativedelta import relativedelta

from decimal import Decimal
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Window, F, Case, When, DecimalField
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
from . import services


@login_required
def home(request):
    """
    Renderiza o painel principal (dashboard) com os dados
    financeiros do usuário logado.
    """
    # Busca os objetos financeiros pertencentes apenas ao usuário da requisição
    contas_bancarias = ContaBancaria.objects.filter(usuario=request.user)
    cartoes_de_credito = CartaoCredito.objects.filter(usuario=request.user)
    total_contas = sum(conta.saldo_calculado for conta in contas_bancarias)

    chart_labels, chart_data = services.gerar_dados_grafico_saldo(request.user)

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
        conciliar = form.cleaned_data.get('conciliar_automaticamente', False)
        form.instance.conciliado = conciliar
        return super().form_valid(form)

class LancamentoListView(LoginRequiredMixin, ListView):
    model = Lancamento
    template_name = 'core/lancamento_list.html'
    context_object_name = 'lancamentos'
    paginate_by = 50

    def get_queryset(self):
        # Pega os parâmetros da URL
        pk = self.kwargs['conta_pk']
        ano = self.kwargs.get('ano')
        mes = self.kwargs.get('mes')

        if ano is None or mes is None:
            hoje = date.today()
            ano = hoje.year
            mes = hoje.month

        self.conta = get_object_or_404(ContaBancaria, pk=pk, usuario=self.request.user)
        
        # Filtra os lançamentos pelo mês e ano selecionados
        return Lancamento.objects.filter(
            conta_bancaria=self.conta,
            data_caixa__year=ano,
            data_caixa__month=mes
        ).com_saldo_parcial().order_by('-data_caixa', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        ano = self.kwargs.get('ano')
        mes = self.kwargs.get('mes')

        if ano is None or mes is None:
            hoje = date.today()
            ano = hoje.year
            mes = hoje.month

        data_selecionada = date(ano, mes, 1)

        # --- CÁLCULO DO SALDO ANTERIOR ---
        # Saldo inicial da conta
        saldo_anterior = self.conta.saldo_inicial
        # Soma/subtrai lançamentos ANTERIORES ao início do mês selecionado
        lancamentos_passados = Lancamento.objects.filter(
            conta_bancaria=self.conta,
            data_caixa__lt=data_selecionada,
        ).aggregate(
            creditos=Sum('valor', filter=Q(tipo='C')),
            debitos=Sum('valor', filter=Q(tipo='D'))
        )
        saldo_anterior += (lancamentos_passados['creditos'] or 0)
        saldo_anterior -= (lancamentos_passados['debitos'] or 0)
        
        # Pós-processamento para o saldo final correto de cada linha
        for lancamento in context['lancamentos']:
            lancamento.saldo_final_linha = saldo_anterior + lancamento.saldo_parcial
        
        # --- PREPARAÇÃO DOS DADOS PARA O COMPONENTE ---
        context['conta'] = self.conta
        context['todas_as_contas'] = ContaBancaria.objects.filter(usuario=self.request.user)
        context['data_selecionada'] = data_selecionada
        context['mes_anterior'] = data_selecionada - relativedelta(months=1)
        context['mes_seguinte'] = data_selecionada + relativedelta(months=1)
        context['saldo_inicial_periodo'] = saldo_anterior
        
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
    
    def form_valid(self, form):
        """
        Sobrescrito para lidar com o checkbox de conciliação e a lógica da fila de edição.
        """
        # Pega o valor do novo campo do formulário
        conciliar = form.cleaned_data.get('conciliar_automaticamente', False)
        # Atualiza o estado de 'conciliado' do objeto ANTES de salvar
        form.instance.conciliado = conciliar
        
        # Salva o objeto normalmente
        self.object = form.save()

        # Inicia a lógica da fila
        queue = self.request.session.get('edition_queue', [])
        current_pk = self.object.pk

        if current_pk in queue:
            queue.remove(current_pk) # Remove o item atual

            if queue: # Se ainda houver itens na fila
                next_id = queue[0]
                self.request.session['edition_queue'] = queue # Salva a fila atualizada
                # Redireciona para a página de edição do próximo item
                return redirect('core:lancamento_update', pk=next_id)
            else:
                # Se a fila acabou, limpa a sessão e vai para o extrato
                self.request.session.pop('edition_queue', None)
                return redirect(self.get_success_url())
        
        # Se não estava em uma fila, comportamento padrão
        return redirect(self.get_success_url())

    def get_success_url(self):
        """Redireciona de volta para o extrato da conta do lançamento."""
        return reverse_lazy('core:lancamento_list_atual', kwargs={'conta_pk': self.object.conta_bancaria.pk})


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
        return reverse_lazy('core:lancamento_list_atual', kwargs={'conta_pk': self.conta_pk})
    
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

            lancamentos_a_revisar, warnings, lancamentos_antigos = services.processar_arquivo_csv(
                csv_file=csv_file,
                conta_selecionada=conta_selecionada
            )
            
            # Armazena os dados processados e o ID da conta na sessão do usuário
            request.session['lancamentos_para_importar'] = lancamentos_a_revisar
            request.session['conta_pk_para_importar'] = conta_selecionada.pk

            context = {
                'lancamentos': lancamentos_a_revisar,
                'conta': conta_selecionada,
                'lancamentos_antigos': lancamentos_antigos, # <-- NOVO CONTEXTO
            }
            
            # Renderiza o template de pré-conciliação
            return render(request, 'core/pre_conciliacao.html', context)

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
            services.recalcular_saldo_conta(conta)
            messages.success(request, f"{len(lancamentos_para_criar)} lançamentos foram importados com sucesso!")
        else:
            messages.warning(request, "Nenhum lançamento foi importado.")
            
        return redirect('core:lancamento_list_atual', conta_pk=conta.pk)

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
                return redirect('core:lancamento_list_atual', conta_pk=lancamento.conta_bancaria.pk)
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
        lancamentos_validos = Lancamento.objects.filter(usuario=request.user, id__in=ids, conciliado=False).order_by('data_caixa', 'id')
        ids_validos = list(lancamentos_validos.values_list('id', flat=True))

        if not ids_validos:
            return JsonResponse({'status': 'info', 'message': 'Todos os lançamentos selecionados já estão conciliados.\nPara alterar lançamentos conciliados, primeiro faça a edição'}, status=200)

        # Salva a fila de IDs válidos na sessão
        request.session['conciliation_queue'] = ids_validos
        
        # Pega o primeiro ID para iniciar o fluxo
        primeiro_id = ids_validos[0]
        
        # Gera a URL de redirecionamento para o primeiro item
        redirect_url = reverse('core:lancamento_conciliar', kwargs={'pk': primeiro_id})
        
        return JsonResponse({'status': 'success', 'redirect_url': redirect_url})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)
    

@require_POST
@login_required
def iniciar_fila_edicao_view(request):
    try:
        data = json.loads(request.body)
        ids = [int(id_str) for id_str in data.get('ids', [])]

        # Apenas validamos se os lançamentos pertencem ao usuário
        lancamentos_validos = Lancamento.objects.filter(
            usuario=request.user, id__in=ids
        ).order_by('data_caixa', 'id')

        ids_para_a_fila = list(lancamentos_validos.values_list('id', flat=True))

        if not ids_para_a_fila:
            return JsonResponse({'status': 'error', 'message': 'Nenhum lançamento válido selecionado.'}, status=400)

        # Usamos uma chave de sessão diferente para a fila de edição
        request.session['edition_queue'] = ids_para_a_fila
        
        primeiro_id = ids_para_a_fila[0]
        
        # Redirecionamos para a view de UPDATE existente
        redirect_url = reverse('core:lancamento_update', kwargs={'pk': primeiro_id})
        
        return JsonResponse({'status': 'success', 'redirect_url': redirect_url})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)