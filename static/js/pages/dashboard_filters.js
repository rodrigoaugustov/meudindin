// static/js/pages/dashboard_filters.js
document.addEventListener('DOMContentLoaded', () => {
    const filterList = document.getElementById('contas-filter-list');
    if (!filterList) return;

    const gridContainer = document.querySelector('.grid[data-ano]');
    const totalContasEl = document.getElementById('total-contas-valor');
    const fluxoCaixaBodyEl = document.getElementById('fluxo-caixa-body');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    async function updateDashboard() {
        const checkboxes = filterList.querySelectorAll('input[type="checkbox"]');
        const selectedIds = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => parseInt(cb.dataset.id));

        const ano = gridContainer.dataset.ano;
        const mes = gridContainer.dataset.mes;

        try {
            const response = await fetch('/dashboard-data/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    ano: ano,
                    mes: mes,
                    contas_ids: selectedIds
                })
            });

            if (!response.ok) throw new Error('A resposta do servidor não foi bem-sucedida.');

            const data = await response.json();

            if (data.status === 'success') {
                // Atualiza o valor total
                totalContasEl.textContent = data.total_contas;

                // Atualiza o gráfico de saldo (chama a função global)
                if (typeof window.updateSaldoChart === 'function') {
                    window.updateSaldoChart(data.saldo_chart);
                }

                // Atualiza o gráfico de despesas (chama a função global)
                if (typeof window.updateDespesasChart === 'function') {
                    window.updateDespesasChart(data.despesas_chart);
                }

                // Atualiza a tabela de fluxo de caixa
                fluxoCaixaBodyEl.innerHTML = ''; // Limpa as linhas existentes
                if (data.fluxo_caixa_tabela.length > 0) {
                    data.fluxo_caixa_tabela.forEach(item => {
                        const row = `
                            <tr class="border-b border-gray-100">
                                <td class="py-2 font-medium text-gray-700">${item.mes}</td>
                                <td class="py-2 text-green-600 text-right">${item.total_creditos}</td>
                                <td class="py-2 text-red-600 text-right">${item.total_debitos}</td>
                            </tr>
                        `;
                        fluxoCaixaBodyEl.insertAdjacentHTML('beforeend', row);
                    });
                } else {
                    fluxoCaixaBodyEl.innerHTML = `<tr><td colspan="3" class="py-4 text-center text-gray-500">Sem dados para este ano.</td></tr>`;
                }
            } else {
                console.error('Erro retornado pelo servidor:', data.message);
            }
        } catch (error) {
            console.error('Erro ao buscar dados do dashboard:', error);
        }
    }

    filterList.addEventListener('change', (e) => {
        if (e.target.matches('input[type="checkbox"]')) {
            updateDashboard();
        }
    });
});