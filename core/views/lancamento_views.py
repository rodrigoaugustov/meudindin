# core/views/lancamento_views.py

import json
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core import services

from ..models import Lancamento, ContaBancaria, CartaoCredito, Categoria, Fatura
from ..forms import LancamentoForm, ConciliacaoForm, RegraCategoriaModalForm


class LancamentoCreateView(LoginRequiredMixin, CreateView):
    model = Lancamento
    form_class = LancamentoForm
    template_name = 'core/lancamento_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['initial'] = kwargs.get('initial', {}) # Garante que initial exista
        
        # Passa a conta ou cartão para o formulário, se presente na URL
        if 'conta_pk' in self.kwargs:
            kwargs['conta'] = get_object_or_404(ContaBancaria, pk=self.kwargs['conta_pk'], usuario=self.request.user)
            kwargs['initial']['data_competencia'] = date.today() # Define a data inicial para conta
        elif 'cartao_pk' in self.kwargs:
            kwargs['cartao'] = get_object_or_404(CartaoCredito, pk=self.kwargs['cartao_pk'], usuario=self.request.user)
            kwargs['initial']['data_competencia'] = date.today() # Define a data inicial para cartão
            
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona o contexto para o template saber qual formulário renderizar
        if 'conta_pk' in self.kwargs:
            context['form_context'] = 'conta'
            context['conta'] = get_object_or_404(ContaBancaria, pk=self.kwargs['conta_pk'], usuario=self.request.user)
        elif 'cartao_pk' in self.kwargs:
            context['form_context'] = 'cartao'
            context['cartao'] = get_object_or_404(CartaoCredito, pk=self.kwargs['cartao_pk'], usuario=self.request.user)
        else:
            context['form_context'] = 'generic'

        # Dados dos cartões para a lógica JS (ainda útil para o form genérico)
        if context['form_context'] != 'conta':
            cartoes = CartaoCredito.objects.filter(usuario=self.request.user)
            cartoes_data = {c.id: {'fechamento': c.dia_fechamento, 'vencimento': c.dia_vencimento} for c in cartoes}
            context['cartoes_data_json'] = mark_safe(json.dumps(cartoes_data))

        context['form_regra_modal'] = RegraCategoriaModalForm(user=self.request.user)
        return context

    def get_success_url(self):
        """
        Retorna a URL de sucesso. Prioriza o parâmetro 'next' na URL.
        Se não houver 'next', redireciona para a página inicial como fallback.
        """
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('core:home')

    def form_valid(self, form):
        form.instance.usuario = self.request.user

        # Se o contexto for específico, garante que a FK correta seja salva
        if 'conta_pk' in self.kwargs:
            form.instance.conta_bancaria_id = self.kwargs['conta_pk']
        elif 'cartao_pk' in self.kwargs:
            form.instance.cartao_credito_id = self.kwargs['cartao_pk']

        # Regra de conciliação: Lançamentos futuros não podem ser marcados como conciliados.
        data_caixa = form.cleaned_data.get('data_caixa')
        conciliar_automaticamente = form.cleaned_data.get('conciliar_automaticamente', False)
        
        if data_caixa and data_caixa <= date.today():
            form.instance.conciliado = conciliar_automaticamente
        else:
            form.instance.conciliado = False
        
        self.object = form.save()

        repeticao = form.cleaned_data.get('repeticao')
        if repeticao == 'RECORRENTE':
            periodicidade = form.cleaned_data.get('periodicidade')
            quantidade = form.cleaned_data.get('quantidade_repeticoes')
            if periodicidade and quantidade:
                services.criar_lancamentos_recorrentes(self.object, periodicidade, quantidade)
                messages.success(self.request, f"{quantidade} lançamentos recorrentes foram criados com sucesso!")
        else:
            messages.success(self.request, "Lançamento criado com sucesso!")

        return redirect(self.get_success_url())

class LancamentoListView(LoginRequiredMixin, ListView):
    model = Lancamento
    template_name = 'core/lancamento_list.html'
    context_object_name = 'lancamentos'
    paginate_by = 50

    def get_queryset(self):
        pk = self.kwargs['conta_pk']
        ano = self.kwargs.get('ano')
        mes = self.kwargs.get('mes')

        self.hoje = date.today()
        if ano is None or mes is None:
            ano = self.hoje.year
            mes = self.hoje.month

        self.conta = get_object_or_404(ContaBancaria, pk=pk, usuario=self.request.user)
        
        # Queryset base
        queryset = Lancamento.objects.filter(
            conta_bancaria=self.conta,
            data_caixa__year=ano,
            data_caixa__month=mes
        )

        # Captura os parâmetros de filtro do GET request
        self.tipo_filtro = self.request.GET.get('tipo', '')
        self.categoria_filtro = self.request.GET.get('categoria', '')
        self.q_filtro = self.request.GET.get('q', '')

        # Aplica os filtros ao queryset
        if self.tipo_filtro:
            queryset = queryset.filter(tipo=self.tipo_filtro)
        
        if self.categoria_filtro:
            queryset = queryset.filter(categoria_id=self.categoria_filtro)

        if self.q_filtro:
            queryset = queryset.filter(descricao__icontains=self.q_filtro)

        return queryset.com_saldo_parcial().order_by('-data_caixa', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        ano = self.kwargs.get('ano')
        mes = self.kwargs.get('mes')

        if ano is None or mes is None:
            hoje = date.today()
            ano = hoje.year
            mes = hoje.month

        data_selecionada = date(ano, mes, 1)

        saldo_anterior = self.conta.saldo_inicial
        lancamentos_passados = Lancamento.objects.filter(
            conta_bancaria=self.conta,
            data_caixa__lt=data_selecionada,
        ).aggregate(
            creditos=Sum('valor', filter=Q(tipo='C')),
            debitos=Sum('valor', filter=Q(tipo='D'))
        )
        saldo_anterior += (lancamentos_passados['creditos'] or 0)
        saldo_anterior -= (lancamentos_passados['debitos'] or 0)
        
        for lancamento in context['lancamentos']:
            lancamento.saldo_final_linha = saldo_anterior + lancamento.saldo_parcial
        
        context['conta'] = self.conta
        context['todas_as_contas'] = ContaBancaria.objects.filter(usuario=self.request.user)
        context['data_selecionada'] = data_selecionada
        context['mes_anterior'] = data_selecionada - relativedelta(months=1)
        context['mes_seguinte'] = data_selecionada + relativedelta(months=1)
        context['saldo_inicial_periodo'] = saldo_anterior
        context['hoje'] = self.hoje
        
        # Adiciona os novos dados de contexto para os filtros
        context['categorias_conta'] = Categoria.objects.filter(
            Q(lancamento__conta_bancaria=self.conta) | Q(usuario__isnull=True)
        ).distinct().order_by('nome')
        context['filtro_tipo_atual'] = self.tipo_filtro
        context['filtro_q_atual'] = self.q_filtro
        
        try:
            context['filtro_categoria_atual'] = int(self.categoria_filtro)
        except (ValueError, TypeError):
            context['filtro_categoria_atual'] = ''
        
        return context
    
class LancamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Lancamento
    form_class = LancamentoForm
    template_name = 'core/lancamento_form.html'

    def get_form(self, form_class=None):
        """Remove os campos de criação de recorrência do formulário de edição."""
        form = super().get_form(form_class)
        form.fields.pop('repeticao', None)
        form.fields.pop('periodicidade', None)
        form.fields.pop('quantidade_repeticoes', None)
        return form

    def get_queryset(self):
        return Lancamento.objects.filter(usuario=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        if self.object:
            initial['conciliar_automaticamente'] = self.object.conciliado
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartoes = CartaoCredito.objects.filter(usuario=self.request.user)
        cartoes_data = {
            c.id: {'fechamento': c.dia_fechamento, 'vencimento': c.dia_vencimento}
            for c in cartoes
        }
        context['cartoes_data_json'] = mark_safe(json.dumps(cartoes_data))
        context['form_regra_modal'] = RegraCategoriaModalForm(user=self.request.user, initial={'categoria': self.object.categoria})
        context['is_recorrente'] = False

        if self.object.recorrencia_id:
            context['is_recorrente'] = True
            # Verifica se existem lançamentos futuros não conciliados na série
            context['future_recurrences_exist'] = Lancamento.objects.filter(
                recorrencia_id=self.object.recorrencia_id,
                data_caixa__gt=self.object.data_caixa,
                conciliado=False
            ).exists()
        return context

    def form_valid(self, form):
        data_caixa = form.cleaned_data.get('data_caixa')
        conciliar_automaticamente = form.cleaned_data.get('conciliar_automaticamente', False)
        if data_caixa and data_caixa <= date.today():
            form.instance.conciliado = conciliar_automaticamente
        else:
            form.instance.conciliado = False

        update_option = self.request.POST.get('update_option')
        original_object = self.get_object() # Pega o estado do objeto ANTES da alteração.

        # Salva o formulário, atualizando a instância do objeto atual.
        self.object = form.save()

        # Agora, se for uma atualização recorrente, propaga as alterações.
        if original_object.recorrencia_id and update_option == 'all':
            # Define quais campos devem ser propagados para os lançamentos futuros.
            fields_to_propagate = ['descricao', 'valor', 'tipo', 'categoria', 'conta_bancaria', 'cartao_credito']
            
            # Busca os lançamentos futuros usando a data original como referência para evitar erros.
            future_lancamentos = Lancamento.objects.filter(
                usuario=self.request.user, recorrencia_id=original_object.recorrencia_id,
                data_caixa__gt=original_object.data_caixa, conciliado=False
            )
            # Prepara os dados para a atualização em massa com os novos valores.
            update_kwargs = {field: getattr(self.object, field) for field in fields_to_propagate}
            updated_count = future_lancamentos.update(**update_kwargs)
            messages.success(self.request, f"Lançamento atualizado. As alterações foram aplicadas a mais {updated_count} lançamento(s) futuro(s).")
        else:
            messages.success(self.request, "Lançamento atualizado com sucesso.")

        queue = self.request.session.get('edition_queue', [])
        current_pk = self.object.pk
        if current_pk in queue:
            queue.remove(current_pk)
            if queue:
                next_id = queue[0]
                self.request.session['edition_queue'] = queue
                return redirect('core:lancamento_update', pk=next_id)
            else:
                self.request.session.pop('edition_queue', None)
                return redirect(self.get_success_url())
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.object.conta_bancaria:
            return reverse_lazy('core:lancamento_list_atual', kwargs={'conta_pk': self.object.conta_bancaria.pk})
        return reverse_lazy('core:home')


class LancamentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Lancamento
    template_name = 'core/lancamento_confirm_delete.html'
    
    def get_queryset(self):
        return Lancamento.objects.filter(usuario=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lancamento = self.get_object()
        context['future_recurrences_exist'] = False
        if lancamento.recorrencia_id:
            # Verifica se existem lançamentos futuros não conciliados na série
            context['future_recurrences_exist'] = Lancamento.objects.filter(
                recorrencia_id=lancamento.recorrencia_id,
                data_caixa__gt=lancamento.data_caixa,
                conciliado=False
            ).exists()
        return context

    def post(self, request, *args, **kwargs):
        """ Sobrescreve o método post para lidar com a lógica de exclusão recorrente. """
        self.object = self.get_object()
        success_url = self.get_success_url()
        delete_option = request.POST.get('delete_option')

        if self.object.recorrencia_id and delete_option == 'all':
            # Exclui este e todos os futuros lançamentos não conciliados da série.
            lancamentos_a_excluir = Lancamento.objects.filter(
                usuario=request.user, recorrencia_id=self.object.recorrencia_id, 
                data_caixa__gte=self.object.data_caixa, conciliado=False
            )
            count = lancamentos_a_excluir.count()
            lancamentos_a_excluir.delete()
            messages.success(request, f"{count} lançamento(s) recorrente(s) foram excluídos.")
        else:
            self.object.delete()
            messages.success(request, "Lançamento excluído com sucesso.")

        return redirect(success_url)

    def get_success_url(self):
        if self.object.conta_bancaria:
            self.conta_pk = self.object.conta_bancaria.pk
            return reverse_lazy('core:lancamento_list_atual', kwargs={'conta_pk': self.conta_pk})
        return reverse_lazy('core:home')
    
@require_POST
@login_required
def excluir_lancamentos_em_massa(request):
    try:
        data = json.loads(request.body)
        ids_selecionados = data.get('ids', [])
        delete_option = data.get('delete_option', 'one') # 'one' ou 'all'

        if not ids_selecionados:
            return JsonResponse({'status': 'error', 'message': 'Nenhum ID fornecido.'}, status=400)

        # Converte para um set para manipulação eficiente e evitar duplicatas
        ids_para_excluir = set(int(id_str) for id_str in ids_selecionados)

        if delete_option == 'all':
            # Busca os lançamentos selecionados que são recorrentes
            lancamentos_recorrentes_selecionados = Lancamento.objects.filter(
                usuario=request.user, 
                pk__in=ids_para_excluir, 
                recorrencia_id__isnull=False
            )
            
            # Para cada um, encontra os futuros e adiciona ao set de exclusão
            for lancamento in lancamentos_recorrentes_selecionados:
                lancamentos_futuros = Lancamento.objects.filter(
                    usuario=request.user,
                    recorrencia_id=lancamento.recorrencia_id,
                    data_caixa__gt=lancamento.data_caixa,
                    conciliado=False
                ).values_list('id', flat=True)
                
                ids_para_excluir.update(lancamentos_futuros)

        # Executa a exclusão em massa de todos os IDs coletados
        lancamentos_a_excluir = Lancamento.objects.filter(usuario=request.user, id__in=list(ids_para_excluir))
        count = lancamentos_a_excluir.count()
        lancamentos_a_excluir.delete()
        return JsonResponse({'status': 'success', 'deleted_count': count})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)

@require_POST
@login_required
def iniciar_fila_conciliacao_view(request):
    try:
        data = json.loads(request.body)
        ids = [int(id_str) for id_str in data.get('ids', [])]
        lancamentos_validos = Lancamento.objects.filter(usuario=request.user, id__in=ids, conciliado=False).order_by('data_caixa', 'id')
        ids_validos = list(lancamentos_validos.values_list('id', flat=True))

        if not ids_validos:
            return JsonResponse({'status': 'info', 'message': 'Todos os lançamentos selecionados já estão conciliados.'}, status=200)

        request.session['conciliation_queue'] = ids_validos
        redirect_url = reverse('core:lancamento_conciliar', kwargs={'pk': ids_validos[0]})
        return JsonResponse({'status': 'success', 'redirect_url': redirect_url})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)

@require_POST
@login_required
def iniciar_fila_edicao_view(request):
    try:
        data = json.loads(request.body)
        ids = [int(id_str) for id_str in data.get('ids', [])]
        lancamentos_validos = Lancamento.objects.filter(usuario=request.user, id__in=ids).order_by('data_caixa', 'id')
        ids_para_a_fila = list(lancamentos_validos.values_list('id', flat=True))

        if not ids_para_a_fila:
            return JsonResponse({'status': 'error', 'message': 'Nenhum lançamento válido selecionado.'}, status=400)

        request.session['edition_queue'] = ids_para_a_fila
        redirect_url = reverse('core:lancamento_update', kwargs={'pk': ids_para_a_fila[0]})
        return JsonResponse({'status': 'success', 'redirect_url': redirect_url})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Requisição inválida.'}, status=400)

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

            if pk in queue:
                queue.remove(pk)
                
            if queue:
                next_id = queue[0]
                request.session['conciliation_queue'] = queue
                return redirect('core:lancamento_conciliar', pk=next_id)
            else:
                request.session.pop('conciliation_queue', None)
                return redirect('core:lancamento_list_atual', conta_pk=lancamento.conta_bancaria.pk)
    else:
        form = ConciliacaoForm(initial={'data_caixa': lancamento.data_caixa.strftime('%Y-%m-%d'), 'valor': lancamento.valor})

    context = {'form': form, 'lancamento': lancamento}
    return render(request, 'core/conciliar_lancamento.html', context)

@login_required
def get_faturas_options_view(request):
    cartao_pk = request.GET.get('cartao_pk')
    data_compra_str = request.GET.get('data_compra')

    if not cartao_pk or not data_compra_str:
        return JsonResponse({'error': 'Parâmetros ausentes.'}, status=400)

    try:
        cartao = get_object_or_404(CartaoCredito, pk=cartao_pk, usuario=request.user)
        data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d').date()
    except (ValueError, CartaoCredito.DoesNotExist):
        return JsonResponse({'error': 'Parâmetros inválidos.'}, status=400)

    # Usa o serviço para encontrar a fatura padrão para a data
    temp_lancamento = Lancamento(usuario=request.user, cartao_credito=cartao, data_competencia=data_compra)
    default_fatura = services.get_or_create_fatura_aberta(temp_lancamento)

    # Constrói o queryset para 'fatura': fatura padrão + 2 anteriores + 2 próximas
    faturas_qs = Fatura.objects.filter(cartao=cartao).order_by('-data_vencimento')
    all_faturas_ordered = list(faturas_qs)
    
    selected_faturas_pks = set()
    if default_fatura:
        try:
            idx = all_faturas_ordered.index(default_fatura)
            faturas_slice = all_faturas_ordered[max(0, idx - 2):min(len(all_faturas_ordered), idx + 3)]
            selected_faturas_pks.update(f.pk for f in faturas_slice)
        except ValueError:
            pass # Fatura recém-criada pode não estar na lista inicial
        selected_faturas_pks.add(default_fatura.pk)

    faturas_options = Fatura.objects.filter(pk__in=selected_faturas_pks).order_by('-data_vencimento')
    faturas_data = [{'pk': f.pk, 'name': f"Fatura Venc. {f.data_vencimento.strftime('%d/%m/%Y')}"} for f in faturas_options]

    return JsonResponse({
        'default_fatura_pk': default_fatura.pk if default_fatura else None,
        'faturas': faturas_data
    })