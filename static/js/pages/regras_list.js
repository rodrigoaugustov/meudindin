// static/js/pages/regras_list.js
document.addEventListener('DOMContentLoaded', function () {
    const sortableList = document.getElementById('regras-list');
    if (!sortableList) return;

    const sortable = new Sortable(sortableList, {
        animation: 150,
        ghostClass: 'bg-blue-100',
        handle: '.handle', // Define a alça para arrastar
        onEnd: function (evt) {
            const ruleIds = Array.from(sortableList.children).map(child => child.dataset.ruleId);
            
            const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

            fetch('/regras/reordenar/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ order: ruleIds })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    alert('Ocorreu um erro ao reordenar as regras.');
                    // Idealmente, reverter a ordem na UI ou recarregar a página
                }
            })
            .catch(error => console.error('Erro ao reordenar:', error));
        }
    });
});