# core/views/categoria_views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from ..models import Categoria
from ..forms import CategoriaForm


class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = 'core/categoria_list.html'
    context_object_name = 'categorias'

    def get_queryset(self):
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