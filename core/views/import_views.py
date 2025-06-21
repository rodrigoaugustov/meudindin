# core/views/import_views.py

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from ..models import Lancamento, ContaBancaria
from ..forms import UnifiedImportForm
from .. import services


@login_required
def importar_unificado_view(request):
    template_name = 'core/importar_unificado.html'
    if request.method == 'POST':
        form = UnifiedImportForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            import_type = form.cleaned_data['import_type']
            conta_selecionada = form.cleaned_data['conta_bancaria']
            import_file = form.cleaned_data['import_file']

            if import_type == 'csv':
                lancamentos_a_revisar, warnings, lancamentos_antigos = services.processar_arquivo_csv(
                    csv_file=import_file, conta_selecionada=conta_selecionada
                )
            elif import_type == 'ofx':
                lancamentos_a_revisar, warnings, lancamentos_antigos = services.processar_arquivo_ofx(
                    ofx_file=import_file, conta_selecionada=conta_selecionada
                )
            else:
                messages.error(request, "Tipo de importação inválido.")
                return redirect('core:importar_unificado')
            
            request.session['lancamentos_para_importar'] = lancamentos_a_revisar
            request.session['conta_pk_para_importar'] = conta_selecionada.pk
            request.session['import_type_para_confirmar'] = import_type

            context = {'lancamentos': lancamentos_a_revisar, 'conta': conta_selecionada, 'warnings': warnings, 'lancamentos_antigos': lancamentos_antigos}
            return render(request, 'core/pre_conciliacao.html', context)
        else:
            messages.error(request, "Houve um erro na validação do formulário. Por favor, corrija os erros abaixo.")
    else: # GET request
        form = UnifiedImportForm(user=request.user)
    
    return render(request, template_name, {'form': form})


@login_required
def confirmar_importacao_view(request):
    if request.method == 'POST':
        lancamentos_data = request.session.pop('lancamentos_para_importar', [])
        conta_pk = request.session.pop('conta_pk_para_importar', None)
        request.session.pop('import_type_para_confirmar', None)
        
        indices_a_ignorar_str = request.POST.get('indices_a_ignorar', '')
        indices_a_ignorar = {int(i) for i in indices_a_ignorar_str.split(',') if i}

        if not lancamentos_data or not conta_pk:
            messages.error(request, "Nenhum dado para importar encontrado ou a sessão expirou. Por favor, tente novamente.")
            return redirect('core:importar_unificado')

        conta = get_object_or_404(ContaBancaria, pk=conta_pk, usuario=request.user)
        
        lancamentos_para_criar = []
        for indice, data in enumerate(lancamentos_data):
            if indice in indices_a_ignorar or data.get('ja_importado'):
                continue

            lancamentos_para_criar.append(Lancamento(
                usuario=request.user, conta_bancaria=conta, data_competencia=data['data_competencia'],
                data_caixa=data['data_caixa'], descricao=data['descricao'], valor=Decimal(data['valor']),
                tipo='C' if data['tipo'] == 'Crédito' else 'D', conciliado=True,
                import_hash=data['import_hash'], numero_documento=data['numero_documento']
            ))

        if lancamentos_para_criar:
            Lancamento.objects.bulk_create(lancamentos_para_criar)
            services.recalcular_saldo_conta(conta)
            messages.success(request, f"{len(lancamentos_para_criar)} lançamentos foram importados com sucesso!")
        else:
            messages.warning(request, "Nenhum lançamento foi importado.")

        return redirect('core:lancamento_list_atual', conta_pk=conta.pk)

    return redirect('core:importar_unificado')