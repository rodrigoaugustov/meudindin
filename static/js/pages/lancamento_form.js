// static/js/pages/lancamento_form.js
document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica para o formulário de Conta Bancária (simples) ---
    const dataCompetenciaEl = document.getElementById('id_data_competencia');
    const dataCaixaEl = document.getElementById('id_data_caixa');
    
    function sincronizarDataCaixa() {
        if (dataCompetenciaEl && dataCaixaEl) {
            dataCaixaEl.value = dataCompetenciaEl.value;
        }
    }
    if (dataCompetenciaEl && dataCaixaEl) {
        dataCompetenciaEl.addEventListener('change', sincronizarDataCaixa);
    }

    // --- Lógica para o formulário de Cartão de Crédito (atualização dinâmica da fatura) ---
    const cartaoCreditoEl = document.getElementById('id_cartao_credito');
    const faturaEl = document.getElementById('id_fatura');

    async function updateFaturaOptions() {
        // Só executa se os elementos necessários existirem (contexto de cartão)
        if (!dataCompetenciaEl || !faturaEl || !cartaoCreditoEl) return;

        const dataCompraStr = dataCompetenciaEl.value;
        const cartaoId = cartaoCreditoEl.value;

        if (!dataCompraStr || !cartaoId) {
            return;
        }

        // Mostra um estado de "carregando"
        faturaEl.disabled = true;
        const originalOption = faturaEl.querySelector('option');
        if (originalOption) {
            originalOption.textContent = 'Carregando...';
        } else {
            // Se não houver nenhuma opção, cria uma temporária
            const loadingOption = document.createElement('option');
            loadingOption.textContent = 'Carregando...';
            faturaEl.appendChild(loadingOption);
        }

        try {
            const url = `/ajax/get-faturas-options/?cartao_pk=${cartaoId}&data_compra=${dataCompraStr}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Falha na resposta do servidor.');
            
            const data = await response.json();

            // Limpa as opções atuais
            faturaEl.innerHTML = '';

            // Adiciona as novas faturas retornadas pela API
            if (data.faturas && data.faturas.length > 0) {
                data.faturas.forEach(fatura => {
                    const option = document.createElement('option');
                    option.value = fatura.pk;
                    option.textContent = fatura.name;
                    faturaEl.appendChild(option);
                });
                // Seleciona a fatura padrão
                if (data.default_fatura_pk) {
                    faturaEl.value = data.default_fatura_pk;
                }
            } else {
                // Caso não retorne nenhuma fatura
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'Nenhuma fatura encontrada';
                faturaEl.appendChild(option);
            }

        } catch (error) {
            console.error("Erro ao buscar faturas:", error);
            // Em caso de erro, mostra uma mensagem no select
            faturaEl.innerHTML = '';
            const errorOption = document.createElement('option');
            errorOption.value = '';
            errorOption.textContent = 'Erro ao carregar faturas';
            faturaEl.appendChild(errorOption);
        } finally {
            // Reabilita o campo
            faturaEl.disabled = false;
        }
    }

    // Adiciona o gatilho para a mudança de data no formulário de cartão
    if (dataCompetenciaEl && faturaEl) {
        dataCompetenciaEl.addEventListener('change', updateFaturaOptions);
    }

    // --- Lógica de recorrência (mantida) ---
    const repeticaoEl = document.getElementById('id_repeticao');
    const opcoesRecorrenciaEl = document.getElementById('opcoes-recorrencia');

    function toggleRecorrencia() {
        if (repeticaoEl && opcoesRecorrenciaEl) {
            if (repeticaoEl.value === 'RECORRENTE') {
                opcoesRecorrenciaEl.classList.remove('hidden');
            } else {
                opcoesRecorrenciaEl.classList.add('hidden');
            }
        }
    }

    if (repeticaoEl) {
        repeticaoEl.addEventListener('change', toggleRecorrencia);
        toggleRecorrencia();
    }

    // --- Lógica do modal de reabertura de fatura (mantida) ---
    const faturaFechadaError = document.getElementById('fatura-fechada-error');
    if (faturaFechadaError) {
        const vencimento = faturaFechadaError.dataset.vencimento;
        const faturaPk = faturaFechadaError.dataset.pk;
        
        // Usa o modal de confirmação genérico de base.html
        const modal = document.getElementById('confirmation-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');
        const confirmBtn = document.getElementById('modal-confirm-button');
        const secondaryBtn = document.getElementById('modal-secondary-button');
        const cancelBtn = document.getElementById('modal-cancel-button');

        if (modal) {
            modalTitle.textContent = 'Fatura Fechada';
            modalBody.textContent = `A fatura com vencimento em ${vencimento} já está fechada. Deseja reabrir a fatura para prosseguir com o lançamento?`;
            
            confirmBtn.textContent = 'Sim, reabrir e salvar';
            secondaryBtn.textContent = 'Não, voltar';
            
            // Esconde o botão de cancelar original e mostra o secundário como "Não"
            cancelBtn.classList.add('hidden');
            secondaryBtn.classList.remove('hidden');

            const closeModal = () => {
                modal.classList.add('hidden');
                // Restaura o estado padrão do modal para que outros scripts possam usá-lo
                cancelBtn.classList.remove('hidden');
                secondaryBtn.classList.add('hidden');
                confirmBtn.onclick = null;
                secondaryBtn.onclick = null;
            };

            secondaryBtn.onclick = closeModal; // O botão "Não" apenas fecha o modal.

            confirmBtn.onclick = () => {
                // Adiciona a confirmação ao formulário e o reenvia.
                const form = document.getElementById('lancamento-form');
                const hiddenInput = document.getElementById('id_reabrir_fatura_confirmado');
                if (hiddenInput) {
                    hiddenInput.value = 'true';
                }
                form.submit();
            };
            modal.classList.remove('hidden');
        }
    }
});