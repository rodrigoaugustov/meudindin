# core/views/import_views.py

import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from ..models import Lancamento, ContaBancaria
from ..forms import UnifiedImportForm, LancamentoForm
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
            
            # Adiciona um formulário de lançamento ao contexto para ser usado como template no editor
            form_lancamento = LancamentoForm(user=request.user)

            context = {
                'lancamentos': lancamentos_a_revisar, 
                'conta': conta_selecionada, 
                'warnings': warnings, 
                'lancamentos_antigos': lancamentos_antigos,
                'form_lancamento': form_lancamento
            }
            return render(request, 'core/pre_conciliacao.html', context)
        else:
            messages.error(request, "Houve um erro na validação do formulário. Por favor, corrija os erros abaixo.")
    else: # GET request
        form = UnifiedImportForm(user=request.user)
    
    return render(request, template_name, {'form': form})

@login_required
def confirmar_importacao_view(request):
    if request.method == 'POST':
        try:
            lancamentos_json = request.POST.get('lancamentos_json')
            lancamentos_data = json.loads(lancamentos_json)
        except (json.JSONDecodeError, TypeError):
            messages.error(request, "Ocorreu um erro ao processar os dados. Tente novamente.")
            return redirect('core:importar_unificado')

        conta_pk = request.session.pop('conta_pk_para_importar', None)
        # Limpa outros dados da sessão para segurança
        request.session.pop('lancamentos_para_importar', None)
        request.session.pop('import_type_para_confirmar', None)

        if not lancamentos_data or not conta_pk:
            messages.error(request, "Nenhum dado para importar encontrado ou a sessão expirou. Por favor, tente novamente.")
            return redirect('core:importar_unificado')

        conta = get_object_or_404(ContaBancaria, pk=conta_pk, usuario=request.user)
        
        lancamentos_para_criar = []
        for data in lancamentos_data:
            # Validação básica dos dados recebidos
            if not all(k in data for k in ['descricao', 'valor', 'tipo', 'data_competencia', 'data_caixa', 'categoria_id', 'import_hash']):
                continue

            lancamentos_para_criar.append(Lancamento(
                usuario=request.user,
                conta_bancaria=conta,
                data_competencia=data['data_competencia'],
                data_caixa=data['data_caixa'],
                descricao=data['descricao'],
                valor=Decimal(data['valor']),
                tipo='C' if data['tipo'] == 'Crédito' else 'D',
                categoria_id=int(data['categoria_id']),
                conciliado=True,
                import_hash=data['import_hash'],
                numero_documento=data.get('numero_documento')
            ))

        if lancamentos_para_criar:
            Lancamento.objects.bulk_create(lancamentos_para_criar)
            services.recalcular_saldo_conta(conta)
            messages.success(request, f"{len(lancamentos_para_criar)} lançamentos foram importados com sucesso!")
        else:
            messages.warning(request, "Nenhum lançamento foi importado.")

        return redirect('core:lancamento_list_atual', conta_pk=conta.pk)

    return redirect('core:importar_unificado')