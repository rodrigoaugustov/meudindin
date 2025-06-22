# core/views/lancamento_views.py

import json
from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core import services

from ..models import Lancamento, ContaBancaria, CartaoCredito, Categoria
from ..forms import LancamentoForm, ConciliacaoForm, RegraCategoriaModalForm


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
        context = super().get_context_data(**kwargs)
        cartoes = CartaoCredito.objects.filter(usuario=self.request.user)
        cartoes_data = {
            c.id: {'fechamento': c.dia_fechamento, 'vencimento': c.dia_vencimento}
            for c in cartoes
        }
        context['cartoes_data_json'] = mark_safe(json.dumps(cartoes_data))
        context['form_regra_modal'] = RegraCategoriaModalForm(user=self.request.user)
        return context

    def form_valid(self, form):
        form.instance.usuario = self.request.user

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
        
        return context
    
class LancamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Lancamento
    form_class = LancamentoForm
    template_name = 'core/lancamento_form.html'

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
        return context

    def form_valid(self, form):
        # Regra de conciliação: Lançamentos futuros não podem ser marcados como conciliados.
        data_caixa = form.cleaned_data.get('data_caixa')
        conciliar_automaticamente = form.cleaned_data.get('conciliar_automaticamente', False)

        if data_caixa and data_caixa <= date.today():
            form.instance.conciliado = conciliar_automaticamente
        else:
            form.instance.conciliado = False
        self.object = form.save()

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
        ids = data.get('ids', [])
        lancamentos_a_excluir = Lancamento.objects.filter(usuario=request.user, id__in=[int(id) for id in ids])
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