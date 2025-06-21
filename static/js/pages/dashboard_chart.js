// static/js/pages/dashboard_chart.js
let saldoChart = null;

window.updateSaldoChart = function(chartData) {
    const labels = chartData.labels || [];
    const dataPoints = chartData.points || [];
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
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + value.toLocaleString('pt-BR');
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false // Remove a legenda
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Saldo: ' + new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed.y);
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