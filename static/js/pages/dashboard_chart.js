// static/js/pages/dashboard_chart.js
let saldoChart = null;

const todayLinePlugin = {
    id: 'todayLine',
    afterDraw: (chart) => {
        // O plugin obtém o índice a partir de seu próprio namespace de opções
        const todayIndex = chart.options.plugins.todayLine.todayIndex;
        if (todayIndex === -1) {
            return; // Não desenha se "hoje" não estiver na visualização atual
        }

        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const yAxis = chart.scales.y;
        const todayX = xAxis.getPixelForValue(todayIndex);
        const todayY = yAxis.getPixelForValue(chart.data.datasets[0].data[todayIndex]);

        // Desenha a linha
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(todayX, yAxis.bottom); // Começa na parte inferior do gráfico
        ctx.lineTo(todayX, todayY);      // Sobe até o ponto de dados
        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(107, 114, 128, 0.8)'; // Uma cor cinza neutra
        ctx.setLineDash([6, 6]); // Torna a linha tracejada
        ctx.stroke();
        ctx.restore();
    }
};

window.updateSaldoChart = function(chartData) {
    const labels = chartData.labels || [];
    const dataPoints = chartData.points || [];
    const todayIndex = chartData.todayIndex;
    const ctx = document.getElementById('saldoDiarioChart');
    const chartContainer = document.getElementById('chart-container');

    if (!ctx || !chartContainer) return;

    if (saldoChart) {
        saldoChart.destroy();
    }

    const green = 'rgba(16, 185, 129, 1)'; // emerald-500
    const red = 'rgba(239, 68, 68, 1)';   // red-500
    const gray = 'rgba(107, 114, 128, 1)';  // gray-500

    if (labels.length > 0 && dataPoints.length > 0) {
        chartContainer.classList.remove('hidden');
        saldoChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            plugins: [todayLinePlugin], // Registra o plugin
            data: {
                labels: labels,
                datasets: [{
                    data: dataPoints,
                    fill: false,
                    tension: 0.1,
                    segment: {
                        borderColor: ctx => {
                            if (ctx.p0.parsed.y > 0 && ctx.p1.parsed.y > 0) return green;
                            if (ctx.p0.parsed.y < 0 && ctx.p1.parsed.y < 0) return red;
                            return gray;
                        },
                        // Adiciona a lógica para a linha tracejada
                        borderDash: ctx => {
                            if (todayIndex !== -1 && ctx.p0.parsed.x >= todayIndex) {
                                return [6, 6]; // Estilo tracejado [linha, espaço]
                            }
                            return undefined; // Linha sólida
                        }
                    },
                    pointBackgroundColor: (context) => {
                        const value = context.raw;
                        if (value > 0) return green;
                        if (value < 0) return red;
                        return gray;
                    },
                    pointBorderColor: (context) => {
                        const value = context.raw;
                        if (value > 0) return green;
                        if (value < 0) return red;
                        return gray;
                    },
                    pointRadius: 3,
                    pointHoverRadius: 5,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: {
                            display: false, // Remove as linhas de grade verticais
                        }
                    },
                    y: {
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + value.toLocaleString('pt-BR');
                            }
                        }
                    }
                },
                plugins: {
                    todayLine: {
                        todayIndex: todayIndex
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                 // Adiciona o prefixo "Saldo Projetado" para datas futuras
                                const prefix = todayIndex !== -1 && context.dataIndex >= todayIndex ? 'Saldo Projetado:' : 'Saldo:';
                                return prefix + ' ' + new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed.y);
                            }
                        }
                    }
                }
            }
        });
    } else {
        chartContainer.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const dataScript = document.getElementById('chart-data');
    if (!dataScript) return;
    const initialChartData = JSON.parse(dataScript.textContent);
    window.updateSaldoChart(initialChartData);
});