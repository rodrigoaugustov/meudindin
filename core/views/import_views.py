# core/views/import_views.py

import json
from decimal import Decimal
from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.signals import post_save

from ..models import Lancamento, ContaBancaria
from ..forms import UnifiedImportForm, LancamentoForm, RegraCategoriaModalForm
from ..signals import atualizar_saldo_conta
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
            form_regra_modal = RegraCategoriaModalForm(user=request.user)

            context = {
                'lancamentos': lancamentos_a_revisar, 
                'conta': conta_selecionada, 
                'warnings': warnings, 
                'lancamentos_antigos': lancamentos_antigos,
                'form_lancamento': form_lancamento,
                'form_regra_modal': form_regra_modal,
            }
            return render(request, 'core/pre_conciliacao.html', context)
        else:
            messages.error(request, "Houve um erro na validação do formulário. Por favor, corrija os erros abaixo.")
    else: # GET request
        form = UnifiedImportForm(user=request.user)
    
    return render(request, template_name, {'form': form})

@login_required
def confirmar_importacao_view(request):
    """
    Processa e salva os lançamentos pré-aprovados pelo usuário.
    """
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
        
        # Desconecta o sinal para evitar recálculos de saldo a cada `save()`
        post_save.disconnect(atualizar_saldo_conta, sender=Lancamento)
        
        try:
            total_criados = 0
            for data in lancamentos_data:
                # Validação básica dos dados recebidos (chaves em camelCase vindas do dataset JS)
                if not all(k in data for k in ['descricao', 'valor', 'tipo', 'dataCompetencia', 'dataCaixa', 'categoriaId', 'importHash']):
                    continue
    
                data_caixa_str = data['dataCaixa']
                data_caixa_obj = datetime.fromisoformat(data_caixa_str).date()
    
                data_competencia_str = data['dataCompetencia']
                data_competencia_obj = datetime.fromisoformat(data_competencia_str).date()
    
                lancamento_base = Lancamento(
                    usuario=request.user,
                    conta_bancaria=conta,
                    data_competencia=data_competencia_obj,
                    data_caixa=data_caixa_obj,
                    descricao=data['descricao'],
                    valor=Decimal(data['valor']),
                    tipo='C' if data['tipo'] == 'Crédito' else 'D',
                    categoria_id=int(data['categoriaId']),
                    import_hash=data['importHash'],
                    numero_documento=data.get('numeroDocumento')
                )
                # Regra de conciliação: Lançamentos importados só são conciliados se a data não for futura.
                lancamento_base.conciliado = data_caixa_obj <= date.today()
    
                lancamento_base.save()
                total_criados += 1
    
                if data.get('repeticao') == 'RECORRENTE':
                    try:
                        quantidade = int(data.get('quantidadeRepeticoes'))
                        periodicidade = data.get('periodicidade')
                        if quantidade > 1 and periodicidade:
                            services.criar_lancamentos_recorrentes(lancamento_base, periodicidade, quantidade)
                            total_criados += (quantidade - 1)
                    except (ValueError, TypeError, KeyError):
                        continue
        finally:
            # Reconecta o sinal, garantindo que ele seja reativado mesmo se ocorrer um erro.
            post_save.connect(atualizar_saldo_conta, sender=Lancamento)

        if total_criados > 0:
            # Agora, recalcula o saldo da conta uma única vez.
            services.recalcular_saldo_conta(conta)
            messages.success(request, f"{total_criados} lançamentos foram importados com sucesso!")
        else:
            messages.warning(request, "Nenhum lançamento foi importado.")

        return redirect('core:lancamento_list_atual', conta_pk=conta.pk)

    return redirect('core:importar_unificado')