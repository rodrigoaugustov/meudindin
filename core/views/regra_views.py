# core/views/regra_views.py
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from ..models import RegraCategoria, Categoria
from ..forms import RegraCategoriaForm, RegraCategoriaModalForm
from .. import services


class RegraCategoriaListView(LoginRequiredMixin, ListView):
    model = RegraCategoria
    template_name = 'core/regra_categoria_list.html'
    context_object_name = 'regras'

    def get_queryset(self):
        return RegraCategoria.objects.filter(usuario=self.request.user).order_by('ordem')


class RegraCategoriaCreateView(LoginRequiredMixin, CreateView):
    model = RegraCategoria
    form_class = RegraCategoriaForm
    template_name = 'core/regra_categoria_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        self.object = form.save()
        return redirect('core:regra_aplicar_retroativo', pk=self.object.pk)


class RegraCategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = RegraCategoria
    form_class = RegraCategoriaForm
    template_name = 'core/regra_categoria_form.html'
    success_url = reverse_lazy('core:regra_list')

    def get_queryset(self):
        return RegraCategoria.objects.filter(usuario=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class RegraCategoriaDeleteView(LoginRequiredMixin, DeleteView):
    model = RegraCategoria
    template_name = 'core/regra_categoria_confirm_delete.html'
    success_url = reverse_lazy('core:regra_list')

    def get_queryset(self):
        return RegraCategoria.objects.filter(usuario=self.request.user)


@login_required
def regra_aplicar_retroativo_view(request, pk):
    regra = get_object_or_404(RegraCategoria, pk=pk, usuario=request.user)
    if request.method == 'POST':
        count = services.aplicar_regra_em_massa(regra)
        messages.success(request, f'{count} lançamentos foram atualizados com a nova regra.')
        return redirect('core:regra_list')
    return render(request, 'core/regra_aplicar_retroativo.html', {'regra': regra})


@require_POST
@login_required
def reordenar_regras_view(request):
    try:
        data = json.loads(request.body)
        rule_ids = data.get('order', [])
        with transaction.atomic():
            for index, rule_id in enumerate(rule_ids):
                RegraCategoria.objects.filter(usuario=request.user, pk=int(rule_id)).update(ordem=index + 1)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_POST
@login_required
def criar_regra_lancamento_view(request):
    form = RegraCategoriaModalForm(request.POST, user=request.user)
    if form.is_valid():
        regra = form.save(commit=False)
        regra.usuario = request.user
        regra.save()

        if form.cleaned_data.get('aplicar_retroativo'):
            services.aplicar_regra_em_massa(regra)

        return JsonResponse({
            'status': 'success',
            'message': 'Regra criada com sucesso!',
            'regra': {'id': regra.pk, 'texto': regra.texto_regra, 'categoria_nome': regra.categoria.nome}
        })
    else:
        return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)