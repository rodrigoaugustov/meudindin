# core/views/conta_views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from ..models import ContaBancaria
from ..forms import ContaBancariaForm


class ContaBancariaListView(LoginRequiredMixin, ListView):
    model = ContaBancaria
    template_name = 'core/conta_bancaria_list.html'
    context_object_name = 'contas'

    def get_queryset(self):
        return ContaBancaria.objects.filter(usuario=self.request.user).order_by('nome_banco')

class ContaBancariaCreateView(LoginRequiredMixin, CreateView):
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'core/conta_bancaria_form.html'
    success_url = reverse_lazy('core:conta_list')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)
    
class ContaBancariaUpdateView(LoginRequiredMixin, UpdateView):
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'core/conta_bancaria_form.html'
    success_url = reverse_lazy('core:conta_list')

    def get_queryset(self):
        return ContaBancaria.objects.filter(usuario=self.request.user)

class ContaBancariaDeleteView(LoginRequiredMixin, DeleteView):
    model = ContaBancaria
    template_name = 'core/conta_bancaria_confirm_delete.html'
    success_url = reverse_lazy('core:conta_list')

    def get_queryset(self):
        return ContaBancaria.objects.filter(usuario=self.request.user)