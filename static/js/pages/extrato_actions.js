// static/js/pages/extrato_actions.js
document.addEventListener('DOMContentLoaded', () => {
    const actionBar = document.getElementById('action-bar');
    const selectionCountEl = document.getElementById('selection-count');
    const selectionTotalEl = document.getElementById('selection-total');
    const checkboxes = document.querySelectorAll('input[type="checkbox"][data-id]');
    
    const btnEditar = document.getElementById('btn-editar');
    const btnExcluir = document.getElementById('btn-excluir');
    const btnConciliar = document.getElementById('btn-conciliar');

    // --- Elementos do Modal de Confirmação Genérico ---
    const modal = document.getElementById('confirmation-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const confirmBtn = document.getElementById('modal-confirm-button');
    const secondaryBtn = document.getElementById('modal-secondary-button');
    const cancelBtn = document.getElementById('modal-cancel-button');


    let selectedItems = new Set();
    let totalValue = 0;

    function updateActionBar() {
        const count = selectedItems.size;
        
        if (count > 0) {
            actionBar.classList.remove('hidden');
            selectionCountEl.textContent = `${count} lançamento${count > 1 ? 's' : ''} marcado${count > 1 ? 's' : ''}`;
            selectionTotalEl.textContent = 'R$ ' + new Intl.NumberFormat('pt-BR', { style: 'decimal', minimumFractionDigits: 2 }).format(totalValue);
        } else {
            actionBar.classList.add('hidden');
        }

        // Habilita/desabilita botão de editar
        btnEditar.disabled = count === 0;
        btnEditar.classList.toggle('text-gray-400', count === 0);
        btnEditar.classList.toggle('cursor-not-allowed', count === 0);

        // O botão de conciliar fica ativo se houver pelo menos um item
        btnConciliar.disabled = count === 0;
        btnConciliar.classList.toggle('text-gray-400', count === 0);
        btnConciliar.classList.toggle('cursor-not-allowed', count === 0);
    }

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const id = e.target.dataset.id;
            const value = parseFloat(e.target.dataset.valor);
            const linha = e.target.closest('li');

            if (e.target.checked) {
                selectedItems.add(id);
                totalValue += value;
                linha.classList.add('bg-blue-50');
                checkbox.classList.add('opacity-100');
            } else {
                selectedItems.delete(id);
                totalValue -= value;
                linha.classList.remove('bg-blue-50');
                checkbox.classList.remove('opacity-100');
            }
            updateActionBar();
        });
    });

    window.clearSelection = function() {
        selectedItems.clear();
        totalValue = 0;
        checkboxes.forEach(cb => cb.checked = false);
        updateActionBar();
    }
    
    btnEditar.addEventListener('click', () => {
        if (selectedItems.size > 0) {
            fetch('/lancamentos/iniciar-edicao/', { // <-- URL da nova view
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({ ids: Array.from(selectedItems) })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    alert(data.message || 'Ocorreu um erro ao iniciar a edição.');
                }
            });
        }
    });

    btnExcluir.addEventListener('click', () => {
        if (selectedItems.size === 0) return;

        // Verifica se algum dos itens selecionados é recorrente
        let isAnyRecurrent = false;
        selectedItems.forEach(id => {
            const checkbox = document.querySelector(`input[data-id="${id}"]`);
            if (checkbox && checkbox.dataset.recorrenciaId) {
                isAnyRecurrent = true;
            }
        });

        if (isAnyRecurrent && modal) {
            // Usa o modal avançado se houver itens recorrentes
            modalTitle.textContent = 'Excluir Lançamentos';
            modalBody.textContent = `Você selecionou lançamentos recorrentes. Deseja excluir apenas os ${selectedItems.size} itens selecionados ou também suas futuras recorrências (não conciliadas)?`;
            confirmBtn.textContent = 'Selecionados e futuros';
            secondaryBtn.textContent = 'Apenas selecionados';
            secondaryBtn.classList.remove('hidden');

            const closeModal = () => modal.classList.add('hidden');
            cancelBtn.onclick = closeModal;
            modal.onclick = (e) => { if (e.target === modal) closeModal(); };

            secondaryBtn.onclick = () => {
                performBulkDelete({ ids: Array.from(selectedItems), delete_option: 'one' });
                closeModal();
            };

            confirmBtn.onclick = () => {
                performBulkDelete({ ids: Array.from(selectedItems), delete_option: 'all' });
                closeModal();
            };

            modal.classList.remove('hidden');
        } else {
            // Usa o confirm simples do navegador para exclusões não recorrentes
            if (confirm(`Tem certeza que deseja excluir ${selectedItems.size} lançamento(s)?`)) {
                performBulkDelete({ ids: Array.from(selectedItems), delete_option: 'one' });
            }
        }
    });

    function performBulkDelete(payload) {
        fetch('/lancamentos/bulk-delete/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('#form-excluir-massa [name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(payload)
        }).then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Ocorreu um erro ao excluir os lançamentos.');
            }
        });
    }

    btnConciliar.addEventListener('click', () => {
        if (selectedItems.size > 0) {
            fetch('/lancamentos/iniciar-conciliacao/', { // <-- URL da nova view de preparação
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('#form-excluir-massa [name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({ ids: Array.from(selectedItems) })
            })
            .then(response => response.json()) // Converte a resposta para JSON
            .then(data => {
                if (data.status === 'success' && data.redirect_url) {
                    // Redireciona para o primeiro item da fila, conforme instruído pelo backend
                    window.location.href = data.redirect_url;
                } else {
                    alert(data.message || 'Ocorreu um erro ao iniciar a conciliação.');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Ocorreu um erro de comunicação com o servidor.');
            });
        }
    });
});