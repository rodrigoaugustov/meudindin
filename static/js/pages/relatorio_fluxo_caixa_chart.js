// static/js/pages/relatorio_fluxo_caixa_chart.js
document.addEventListener('DOMContentLoaded', function() {
    const dataScript = document.getElementById('fluxo-caixa-chart-data');
    if (!dataScript) return;

    const chartData = JSON.parse(dataScript.textContent);
    const ctx = document.getElementById('fluxoCaixaChart');

    if (!chartData || !ctx) return;

    const fluxoCaixaChart = new Chart(ctx.getContext('2d'), {
        type: 'bar', // Tipo base do gráfico
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'Entradas',
                    data: chartData.data_creditos,
                    backgroundColor: 'rgba(75, 192, 192, 0.6)', // Verde
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1,
                    yAxisID: 'y', // Eixo principal
                },
                {
                    label: 'Saídas',
                    data: chartData.data_debitos,
                    backgroundColor: 'rgba(255, 99, 132, 0.6)', // Vermelho
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1,
                    yAxisID: 'y', // Eixo principal
                },
                {
                    label: 'Saldo do Mês',
                    data: chartData.data_saldo,
                    type: 'line', // Sobrescreve o tipo para este dataset
                    borderColor: 'rgba(54, 162, 235, 1)', // Azul
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    fill: false,
                    tension: 0.1,
                    yAxisID: 'y', // Eixo principal
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value, index, values) {
                            return 'R$ ' + value.toLocaleString('pt-BR');
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                },
                legend: {
                    position: 'top',
                }
            }
        }
    });
});