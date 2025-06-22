// static/js/pages/lancamento_form.js
document.addEventListener('DOMContentLoaded', function() {
    // Dados dos cartões passados pela View através de um script tag
    const cartoesDataEl = document.getElementById('cartoes-data-json');
    if (!cartoesDataEl) return;
    const cartoesData = JSON.parse(cartoesDataEl.textContent);

    // Seleciona os elementos do DOM
    const dataCompetenciaEl = document.getElementById('id_data_competencia');
    const dataCaixaEl = document.getElementById('id_data_caixa');
    const contaBancariaEl = document.getElementById('id_conta_bancaria');
    const cartaoCreditoEl = document.getElementById('id_cartao_credito');

    function calcularDataCaixa() {
        // Verifica se os elementos essenciais existem
        if (!dataCompetenciaEl || !dataCaixaEl) return;
        
        const dataCompetenciaStr = dataCompetenciaEl.value;
        if (!dataCompetenciaStr) return;

        // Adiciona T12:00:00 para evitar problemas de fuso horário ao converter
        const competencia = new Date(dataCompetenciaStr + 'T12:00:00');
        
        // Se uma conta bancária for selecionada, a data de caixa é a mesma da competência
        if (contaBancariaEl && contaBancariaEl.value) {
            dataCaixaEl.value = dataCompetenciaStr;
            return;
        }

        // Se um cartão de crédito for selecionado, calcula a data de vencimento da fatura
        if (cartaoCreditoEl && cartaoCreditoEl.value) {
            const cartaoId = cartaoCreditoEl.value;
            const cartaoInfo = cartoesData[cartaoId];

            if (cartaoInfo) {
                const diaCompetencia = competencia.getDate();
                const diaFechamento = cartaoInfo.fechamento;
                let dataVencimento = new Date(competencia);
                
                // Se a compra foi feita após o fechamento, a fatura vence no mês seguinte
                if (diaCompetencia > diaFechamento) {
                    dataVencimento.setMonth(dataVencimento.getMonth() + 1);
                }
                dataVencimento.setDate(cartaoInfo.vencimento);
                
                // Formata a data para YYYY-MM-DD
                const ano = dataVencimento.getFullYear();
                const mes = String(dataVencimento.getMonth() + 1).padStart(2, '0');
                const dia = String(dataVencimento.getDate()).padStart(2, '0');
                
                dataCaixaEl.value = `${ano}-${mes}-${dia}`;
            }
            return;
        }

        // Se nenhum dos dois for selecionado, limpa a data de caixa
        dataCaixaEl.value = '';
    }

    // Adiciona os gatilhos
    if (dataCompetenciaEl) dataCompetenciaEl.addEventListener('change', calcularDataCaixa);
    if (contaBancariaEl) contaBancariaEl.addEventListener('change', calcularDataCaixa);
    if (cartaoCreditoEl) cartaoCreditoEl.addEventListener('change', calcularDataCaixa);

    // Roda a função uma vez no carregamento da página para o caso de edição
    calcularDataCaixa();

    // --- Nova lógica para recorrência ---
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

    // --- Nova lógica para o modal de reabertura de fatura ---
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