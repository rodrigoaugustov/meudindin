// static/js/pages/doughnut_chart.js
document.addEventListener('DOMContentLoaded', function() {
    const dataScript = document.getElementById('despesas-chart-data');
    if (!dataScript) return;

    const chartData = JSON.parse(dataScript.textContent);
    if (!chartData || !chartData.condensado || !chartData.condensado.labels.length) {
        // Se não há dados, não faz nada
        return;
    }

    const ctx = document.getElementById('despesasCategoriaChart').getContext('2d');
    let doughnutChartInstance = null;
    let isExpanded = false;

    // Paleta de cores para o gráfico
    const defaultColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
        '#EC4899', '#6366F1', '#F97316', '#06B6D4', '#D946EF'
    ];
    const othersColor = '#6B7280'; // Cinza para a categoria "Outros"

    function getChartColors(labels) {
        return labels.map((label, index) => {
            if (label === 'Outros') return othersColor;
            return defaultColors[index % defaultColors.length];
        });
    }

    function updateChart(data, labels) {
        if (doughnutChartInstance) {
            doughnutChartInstance.destroy();
        }

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
                        updateChart(chartData.condensado.data, chartData.condensado.labels);
                        isExpanded = false;
                    } else if (points.length) {
                        const clickedLabel = doughnutChartInstance.data.labels[points[0].index];
                        if (clickedLabel === 'Outros') {
                            updateChart(chartData.completo.data, chartData.completo.labels);
                            isExpanded = true;
                        }
                    }
                }
            }
        });
    }

    // Renderiza o gráfico inicial com os dados condensados
    updateChart(chartData.condensado.data, chartData.condensado.labels);
});