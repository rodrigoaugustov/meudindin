# core/views/cartao_views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from ..models import CartaoCredito
from ..forms import CartaoCreditoForm


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