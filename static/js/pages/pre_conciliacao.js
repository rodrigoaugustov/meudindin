// static/js/pages/pre_conciliacao.js

document.addEventListener('DOMContentLoaded', function() {
    const tableBody = document.getElementById('lancamentos-table-body');
    const editorContainer = document.getElementById('editor-container');
    const editorForm = document.getElementById('lancamento-editor-form');
    const editorPlaceholder = document.getElementById('editor-placeholder');
    const confirmationForm = document.getElementById('form-confirmacao');
    const lancamentosJsonInput = document.getElementById('lancamentos_json');

    if (!tableBody || !editorContainer || !confirmationForm) return;

    let selectedRow = null;

    // 1. Event Listener para seleção de linha na tabela
    tableBody.addEventListener('click', (e) => {
        const row = e.target.closest('tr');
        // Ignora cliques em botões de ação ou em linhas já importadas
        if (!row || e.target.closest('button') || row.classList.contains('pointer-events-none')) {
            return;
        }

        // Alterna a seleção da linha
        if (selectedRow) {
            selectedRow.classList.remove('bg-blue-100', 'ring-2', 'ring-blue-200');
        }
        row.classList.add('bg-blue-100', 'ring-2', 'ring-blue-200');
        selectedRow = row;

        // Garante que os dados de recorrência existam no dataset ao selecionar a linha pela primeira vez.
        // Isso torna o estado mais previsível e evita problemas se o usuário não interagir com os campos de recorrência.
        if (typeof selectedRow.dataset.repeticao === 'undefined') {
            selectedRow.dataset.repeticao = 'UNICA';
        }
        if (typeof selectedRow.dataset.periodicidade === 'undefined') {
            selectedRow.dataset.periodicidade = 'MENSAL';
        }
        if (typeof selectedRow.dataset.quantidadeRepeticoes === 'undefined') {
            selectedRow.dataset.quantidadeRepeticoes = '2';
        }

        // Preenche o formulário de edição com os dados da linha
        populateEditor(row.dataset);

        // Exibe o editor
        editorPlaceholder.classList.add('hidden');
        editorForm.classList.remove('hidden');
    });

    // 2. Função para preencher o editor com os dados
    function populateEditor(data) {
        document.getElementById('editor_descricao').value = data.descricao;
        document.getElementById('editor_valor').value = data.valor;
        document.getElementById('editor_tipo').value = data.tipo === 'Crédito' ? 'C' : 'D';
        document.getElementById('editor_categoria').value = data.categoriaId;
        document.getElementById('editor_data_competencia').value = data.dataCompetencia;
        document.getElementById('editor_data_caixa').value = data.dataCaixa;
        // Os dados de recorrência agora são lidos diretamente do dataset, que já foi inicializado.
        document.getElementById('editor_repeticao').value = data.repeticao;
        document.getElementById('editor_periodicidade').value = data.periodicidade;
        document.getElementById('editor_quantidade_repeticoes').value = data.quantidadeRepeticoes;
        toggleEditorRecorrencia();
    }

    // 3. Event listener para mudanças nos campos do formulário de edição
    // Usar o evento 'change' é mais robusto para todos os tipos de campos de formulário,
    // especialmente para <select>, garantindo que a alteração seja capturada de forma confiável.
    // O evento 'input' pode não ser disparado de forma consistente para dropdowns em todos os cenários.
    editorForm.addEventListener('change', (e) => {
        if (!selectedRow) return;

        const fieldName = e.target.name;
        const value = e.target.value;

        // Mapeia o nome do campo para a chave do dataset e a célula da tabela
        const fieldMap = {
            'descricao': { datasetKey: 'descricao', cellClass: '.descricao-cell' },
            'valor': { datasetKey: 'valor', cellClass: '.valor-cell' },
            'tipo': { datasetKey: 'tipo', cellClass: '.valor-cell' },
            'categoria': { datasetKey: 'categoriaId', cellClass: '.categoria-nome-cell' },
            // Mapeia os nomes dos campos do formulário para as chaves do dataset
            'data_caixa': { datasetKey: 'dataCaixa', cellClass: '.data-caixa-cell' },
            'data_competencia': { datasetKey: 'dataCompetencia', cellClass: null },
            'repeticao': { datasetKey: 'repeticao', cellClass: null },
            'periodicidade': { datasetKey: 'periodicidade', cellClass: null },
            'quantidade_repeticoes': { datasetKey: 'quantidadeRepeticoes', cellClass: null },
        };

        const mapping = fieldMap[fieldName];
        if (!mapping) return;

        // Atualiza o dataset da linha selecionada
        if (fieldName === 'tipo') {
            selectedRow.dataset[mapping.datasetKey] = e.target.options[e.target.selectedIndex].text;
        } else {
            selectedRow.dataset[mapping.datasetKey] = value;
        }

        // Se o campo de repetição foi alterado, lida com a UI e os valores padrão
        if (fieldName === 'repeticao') {
            toggleEditorRecorrencia();
            // Se mudou para RECORRENTE, garante que os valores padrão sejam salvos no dataset
            if (value === 'RECORRENTE') {
                selectedRow.dataset.periodicidade = document.getElementById('editor_periodicidade').value;
                selectedRow.dataset.quantidadeRepeticoes = document.getElementById('editor_quantidade_repeticoes').value;
            }
        }

        // Atualiza a célula correspondente na tabela para feedback visual imediato
        const cell = selectedRow.querySelector(mapping.cellClass);
        if (cell) {
            if (fieldName === 'categoria') {
                cell.textContent = e.target.options[e.target.selectedIndex].text;
            } else if (fieldName === 'data_caixa') {
                cell.textContent = value.split('-').reverse().join('/');
            } else if (fieldName === 'valor' || fieldName === 'tipo') {
                updateValorCell(selectedRow);
            } else {
                cell.textContent = value;
            }
        }
    });

    // Função auxiliar para atualizar a célula de valor (que depende do tipo)
    function updateValorCell(row) {
        const valor = parseFloat(row.dataset.valor).toFixed(2);
        const tipo = row.dataset.tipo;
        const valorCell = row.querySelector('.valor-cell');
        const sinal = tipo === 'Crédito' ? '+' : '-';
        valorCell.textContent = `${sinal} R$ ${valor}`;
        valorCell.className = `valor-cell px-4 py-4 whitespace-nowrap text-sm text-right ${tipo === 'Crédito' ? 'text-green-600' : 'text-red-600'}`;
    }

    // 4. Event listener para o envio do formulário de confirmação final
    confirmationForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const lancamentosParaEnviar = [];
        const rows = tableBody.querySelectorAll('tr');

        rows.forEach(row => {
            // Inclui apenas linhas que não foram marcadas para exclusão e não foram previamente importadas
            if (!row.classList.contains('line-through') && !row.classList.contains('pointer-events-none')) {
                lancamentosParaEnviar.push(row.dataset);
            }
        });

        lancamentosJsonInput.value = JSON.stringify(lancamentosParaEnviar);
        confirmationForm.submit();
    });

    // --- Lógica para controlar a visibilidade dos campos de recorrência ---
    const editorRepeticaoEl = document.getElementById('editor_repeticao');
    const editorOpcoesRecorrenciaEl = document.getElementById('editor-opcoes-recorrencia');

    function toggleEditorRecorrencia() {
        if (editorRepeticaoEl && editorRepeticaoEl.value === 'RECORRENTE') {
            editorOpcoesRecorrenciaEl.classList.remove('hidden');
        } else {
            editorOpcoesRecorrenciaEl.classList.add('hidden');
        }
    }
});

// Função global para o botão de excluir linha (reutilizada)
function excluirLinha(botao) {
    const linha = botao.closest('tr');
    if (!linha) return;

    // Alterna a classe que marca a linha como "excluída"
    linha.classList.toggle('line-through');
    linha.classList.toggle('text-gray-400');
    linha.classList.toggle('bg-red-50');
    botao.title = linha.classList.contains('line-through') ? "Reincluir este lançamento" : "Não importar este lançamento";
}