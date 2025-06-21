// static/js/pages/lancamento_form_rules.js
document.addEventListener('DOMContentLoaded', function() {
    const openModalBtn = document.getElementById('btn-criar-regra-modal');
    const modal = document.getElementById('modal-criar-regra');
    const closeModalBtn = document.getElementById('btn-fechar-modal-regra');
    const formCriarRegra = document.getElementById('form-criar-regra');

    if (!openModalBtn || !modal || !closeModalBtn || !formCriarRegra) return;

    // Abrir modal e pré-preencher dados
    openModalBtn.addEventListener('click', () => {
        const descricao = document.getElementById('id_descricao').value;
        const categoriaId = document.getElementById('id_categoria').value;
        
        if (!descricao) {
            alert('Por favor, preencha a descrição do lançamento primeiro.');
            return;
        }
        
        document.getElementById('id_texto_regra_modal').value = descricao;
        if (categoriaId) {
            document.getElementById('id_categoria_modal').value = categoriaId;
        }
        
        modal.classList.remove('hidden');
    });

    // Fechar modal
    const fecharModal = () => modal.classList.add('hidden');
    closeModalBtn.addEventListener('click', fecharModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) fecharModal();
    });
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            fecharModal();
        }
    });

    // Lidar com a submissão do formulário via Fetch API
    formCriarRegra.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = new FormData(formCriarRegra);
        const submitButton = formCriarRegra.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Salvando...';

        fetch(formCriarRegra.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
                fecharModal();
                formCriarRegra.reset();
            } else {
                showToast('Erro ao criar regra. Verifique os campos.', 'error');
            }
        })
        .catch(error => showToast('Ocorreu um erro de comunicação.', 'error'))
        .finally(() => {
            submitButton.disabled = false;
            submitButton.textContent = 'Salvar Regra';
        });
    });
});