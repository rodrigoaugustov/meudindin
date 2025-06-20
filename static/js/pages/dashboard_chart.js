// static/js/pages/dashboard_chart.js
document.addEventListener('DOMContentLoaded', function() {
    // 1. Encontra o script tag com os dados
    const dataScript = document.getElementById('chart-data');
    if (!dataScript) return;

    // 2. Lê e faz o parse do conteúdo do script tag
    const chartData = JSON.parse(dataScript.textContent);
    
    const labels = chartData.labels || [];
    const dataPoints = chartData.points || [];

    // 3. Verifica se há dados para renderizar
    if (labels.length > 0 && dataPoints.length > 0) {
        const ctx = document.getElementById('saldoDiarioChart');
        if (ctx) {
            // ... (toda a lógica new Chart(...) permanece exatamente a mesma) ...
            const saldoChart = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Saldo Consolidado',
                        data: dataPoints,
                        // ... (outras opções de estilo)
                    }]
                },
                options: {
                    // ... (todas as opções de configuração)
                }
            });
        }
    }
});