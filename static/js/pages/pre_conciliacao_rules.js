// static/js/pages/pre_conciliacao_rules.js
document.addEventListener('DOMContentLoaded', function() {
    // O editor de lançamento e o botão de criar regra estão dentro de um contêiner.
    // Usamos delegação de eventos no contêiner, pois o botão pode não estar visível no carregamento da página.
    const editorContainer = document.getElementById('editor-container');
    if (!editorContainer) return;

    const modal = document.getElementById('modal-criar-regra');
    const closeModalBtn = document.getElementById('btn-fechar-modal-regra');
    const formCriarRegra = document.getElementById('form-criar-regra');

    // Verifica se os elementos do modal existem
    if (!modal || !closeModalBtn || !formCriarRegra) return;

    // 1. Abrir o modal e pré-preencher os dados
    editorContainer.addEventListener('click', (e) => {
        // Só age se o clique foi no botão de criar regra
        if (e.target.id !== 'btn-criar-regra-modal') {
            return;
        }

        // Pega os valores dos campos do editor (com IDs 'editor_*')
        const descricao = document.getElementById('editor_descricao').value;
        const categoriaId = document.getElementById('editor_categoria').value;
        
        if (!descricao) {
            showToast('Por favor, preencha a descrição do lançamento primeiro.', 'warning');
            return;
        }
        
        // Preenche o formulário do modal
        document.getElementById('id_texto_regra_modal').value = descricao;
        if (categoriaId) {
            document.getElementById('id_categoria_modal').value = categoriaId;
        }
        
        modal.classList.remove('hidden');
    });

    // 2. Lógica para fechar o modal (genérica)
    const fecharModal = () => modal.classList.add('hidden');
    closeModalBtn.addEventListener('click', fecharModal);
    modal.addEventListener('click', (e) => {
        // Fecha se clicar no fundo escuro
        if (e.target === modal) fecharModal();
    });
    window.addEventListener('keydown', (e) => {
        // Fecha se pressionar a tecla 'Escape'
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            fecharModal();
        }
    });

    // 3. Lidar com a submissão do formulário do modal via Fetch API (genérico)
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
        .catch(error => showToast('Ocorreu um erro de comunicação com o servidor.', 'error'))
        .finally(() => {
            submitButton.disabled = false;
            submitButton.textContent = 'Salvar Regra';
        });
    });
});