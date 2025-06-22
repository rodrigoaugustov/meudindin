# core/views/fatura_views.py
from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.views.generic import DetailView, ListView

from ..models import Fatura, CartaoCredito
from .. import services


class FaturaListView(LoginRequiredMixin, ListView):
    model = Fatura
    template_name = 'core/fatura_list.html'
    context_object_name = 'faturas'

    def get_queryset(self):
        cartao_pk = self.kwargs['cartao_pk']
        ano = self.kwargs.get('ano')
        mes = self.kwargs.get('mes')

        if ano is None or mes is None:
            hoje = date.today()
            ano = hoje.year
            mes = hoje.month
        
        self.cartao = get_object_or_404(CartaoCredito, pk=cartao_pk, usuario=self.request.user)

        return Fatura.objects.filter(
            cartao=self.cartao,
            data_vencimento__year=ano,
            data_vencimento__month=mes
        ).order_by('-data_vencimento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        ano = self.kwargs.get('ano')
        mes = self.kwargs.get('mes')

        if ano is None or mes is None:
            hoje = date.today()
            ano = hoje.year
            mes = hoje.month

        data_selecionada = date(ano, mes, 1)

        context['cartao_selecionado'] = self.cartao
        context['todos_os_cartoes'] = CartaoCredito.objects.filter(usuario=self.request.user).order_by('nome_cartao')
        context['data_selecionada'] = data_selecionada
        context['mes_anterior'] = data_selecionada - relativedelta(months=1)
        context['mes_seguinte'] = data_selecionada + relativedelta(months=1)
        
        return context

class FaturaDetailView(LoginRequiredMixin, DetailView):
    model = Fatura
    template_name = 'core/fatura_detail.html'
    context_object_name = 'fatura'

    def get_queryset(self):
        return Fatura.objects.filter(usuario=self.request.user).prefetch_related('lancamentos__categoria')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoje'] = date.today()
        return context


@login_required
@require_POST
def fechar_fatura_view(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk, usuario=request.user)
    
    data_pagamento_str = request.POST.get('data_pagamento')
    if not data_pagamento_str:
        messages.error(request, "A data de pagamento é obrigatória.")
        return redirect('core:fatura_detail', pk=fatura.pk)

    try:
        data_pagamento = date.fromisoformat(data_pagamento_str)
        lancamento_pagamento = services.fechar_fatura(fatura, data_pagamento)
        if lancamento_pagamento:
            messages.success(request, "Fatura fechada e pagamento agendado com sucesso!")
        else:
            messages.warning(request, "A fatura não pôde ser fechada (verifique o status ou valor).")
    except (ValueError, TypeError):
        messages.error(request, "Formato de data inválido.")

    return redirect('core:fatura_detail', pk=fatura.pk)

@login_required
@require_POST
def reabrir_fatura_view(request, pk):
    fatura = get_object_or_404(Fatura, pk=pk, usuario=request.user)
    
    sucesso = services.reabrir_fatura(fatura)
    if sucesso:
        messages.success(request, "Fatura reaberta com sucesso!")
    else:
        messages.error(request, "Não foi possível reabrir a fatura. Verifique se o pagamento já foi conciliado.")
        
    return redirect('core:fatura_detail', pk=fatura.pk)