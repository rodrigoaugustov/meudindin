// static/js/pages/doughnut_chart.js
let doughnutChartInstance = null;
let isExpanded = false;
let fullChartData = {}; // Armazena os dados completos para a funcionalidade de expandir

window.updateDespesasChart = function(chartData) {
    fullChartData = chartData; // Atualiza os dados globais
    // Paleta de cores para o gráfico
    const defaultColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
        '#EC4899', '#6366F1', '#F97316', '#06B6D4', '#D946EF'
    ];
    const othersColor = '#6B7280'; // Cinza para a categoria "Outros"

    const chartContainer = document.getElementById('despesas-chart-container');
    const noDataEl = document.getElementById('no-despesas-data');

    if (!chartContainer || !noDataEl) return;

    if (doughnutChartInstance) {
        doughnutChartInstance.destroy();
    }

    if (!chartData || !chartData.condensado || !chartData.condensado.labels.length) {
        chartContainer.classList.add('hidden');
        noDataEl.classList.remove('hidden');
        return;
    }

    chartContainer.classList.remove('hidden');
    noDataEl.classList.add('hidden');

    function getChartColors(labels) {
        return labels.map((label, index) => {
            if (label === 'Outros') return othersColor;
            return defaultColors[index % defaultColors.length];
        });
    }

    function renderDoughnut(data, labels) {
        if (doughnutChartInstance) {
            doughnutChartInstance.destroy();
        }

        const ctx = document.getElementById('despesasCategoriaChart').getContext('2d');
        doughnutChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Despesas por Categoria',
                    data: data,
                    backgroundColor: getChartColors(labels),
                    borderColor: '#ffffff',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed !== null) {
                                    label += new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed);
                                }
                                return label;
                            }
                        }
                    }
                },
                onClick: (e) => {
                    const points = doughnutChartInstance.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
                    if (isExpanded) {
                        renderDoughnut(fullChartData.condensado.data, fullChartData.condensado.labels);
                        isExpanded = false;
                    } else if (points.length) {
                        const clickedLabel = doughnutChartInstance.data.labels[points[0].index];
                        if (clickedLabel === 'Outros') {
                            renderDoughnut(fullChartData.completo.data, fullChartData.completo.labels);
                            isExpanded = true;
                        }
                    }
                }
            }
        });
    }
    
    isExpanded = false;
    renderDoughnut(chartData.condensado.data, chartData.condensado.labels);
}

document.addEventListener('DOMContentLoaded', function() {
    const dataScript = document.getElementById('despesas-chart-data');
    if (!dataScript) return;
    const initialChartData = JSON.parse(dataScript.textContent);
    window.updateDespesasChart(initialChartData);
});