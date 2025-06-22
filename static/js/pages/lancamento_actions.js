// static/js/pages/lancamento_actions.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Elementos do Modal ---
    const modal = document.getElementById('confirmation-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const confirmBtn = document.getElementById('modal-confirm-button');
    const secondaryBtn = document.getElementById('modal-secondary-button');
    const cancelBtn = document.getElementById('modal-cancel-button');

    if (!modal) return;

    const closeModal = () => modal.classList.add('hidden');
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // --- Lógica para o Formulário de Edição ---
    const lancamentoForm = document.getElementById('lancamento-form');
    const saveBtn = document.getElementById('btn-save-lancamento');

    if (lancamentoForm) {
        lancamentoForm.addEventListener('submit', (e) => {
            const isRecurrent = lancamentoForm.dataset.isRecurrent === 'true';
            const futureExists = lancamentoForm.dataset.futureRecurrencesExist === 'true';

            // Se o campo de opção já foi adicionado pelo modal, permite o envio.
            if (lancamentoForm.querySelector('input[name="update_option"]')) {
                return;
            }

            if (isRecurrent && futureExists) {
                e.preventDefault(); // Impede o envio do formulário para mostrar o modal.
                // Mostra o modal de confirmação
                modalTitle.textContent = 'Atualizar Lançamento Recorrente';
                modalBody.textContent = 'Você deseja aplicar esta alteração apenas para este lançamento ou para este e todos os futuros (não conciliados)?';
                confirmBtn.textContent = 'Este e os futuros';
                secondaryBtn.textContent = 'Apenas este';
                
                secondaryBtn.classList.remove('hidden');

                // Ação para "Apenas este"
                secondaryBtn.onclick = () => {
                    appendHiddenInput(lancamentoForm, 'update_option', 'one');
                    lancamentoForm.submit();
                };

                // Ação para "Este e todos os futuros"
                confirmBtn.onclick = () => {
                    appendHiddenInput(lancamentoForm, 'update_option', 'all');
                    lancamentoForm.submit();
                };

                modal.classList.remove('hidden');
            }
            // Se não for recorrente, o formulário é enviado normalmente (sem preventDefault).
        });
    }

    // --- Lógica para o Formulário de Exclusão ---
    const deleteForm = document.getElementById('delete-form');

    if (deleteForm) {
        deleteForm.addEventListener('submit', (e) => {
            const isRecurrent = deleteForm.dataset.isRecurrent === 'true';
            const futureExists = deleteForm.dataset.futureRecurrencesExist === 'true';

            // Se o campo de opção já foi adicionado, permite o envio.
            if (deleteForm.querySelector('input[name="delete_option"]')) {
                return;
            }

            if (isRecurrent && futureExists) {
                e.preventDefault(); // Impede o envio do formulário.

                // Mostra o modal de confirmação
                modalTitle.textContent = 'Excluir Lançamento Recorrente';
                modalBody.textContent = 'Você deseja excluir apenas este lançamento ou este e todos os futuros (não conciliados)?';
                confirmBtn.textContent = 'Excluir este e futuros';
                secondaryBtn.textContent = 'Excluir apenas este';

                secondaryBtn.classList.remove('hidden');

                // Ação para "Apenas este"
                secondaryBtn.onclick = () => {
                    appendHiddenInput(deleteForm, 'delete_option', 'one');
                    deleteForm.submit();
                };

                // Ação para "Este e todos os futuros"
                confirmBtn.onclick = () => {
                    appendHiddenInput(deleteForm, 'delete_option', 'all');
                    deleteForm.submit();
                };

                modal.classList.remove('hidden');
            }
            // Se não for recorrente, o formulário é enviado normalmente.
        });
    }

    /**
     * Adiciona um campo hidden a um formulário antes de submetê-lo.
     * @param {HTMLFormElement} form - O formulário ao qual o campo será adicionado.
     * @param {string} name - O nome do campo.
     * @param {string} value - O valor do campo.
     */
    function appendHiddenInput(form, name, value) {
        // Remove qualquer campo com o mesmo nome para evitar duplicatas
        const existingInput = form.querySelector(`input[name="${name}"]`);
        if (existingInput) {
            existingInput.remove();
        }

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    }
});