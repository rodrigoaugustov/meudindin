// static/js/components/toast.js

/**
 * Exibe uma notificação toast no canto superior direito da tela.
 * @param {string} message A mensagem a ser exibida.
 * @param {string} type O tipo de notificação ('success', 'error', 'warning', 'info').
 * @param {number} duration Duração em milissegundos para a notificação ser exibida.
 */
function showToast(message, type = 'success', duration = 5000) {
    // Cria um contêiner para os toasts se ele ainda não existir
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed top-20 right-5 z-50 space-y-3';
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    
    // Mapeia o tipo para as classes do Tailwind
    const typeClasses = {
        success: 'bg-green-100 border-green-200 text-green-800',
        error: 'bg-red-100 border-red-200 text-red-800',
        warning: 'bg-yellow-100 border-yellow-200 text-yellow-800',
        info: 'bg-blue-100 border-blue-200 text-blue-800'
    };

    const classes = typeClasses[type] || typeClasses.info;

    toast.className = `p-4 rounded-md border shadow-lg transition-opacity duration-300 opacity-0 ${classes}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);

    // Animação de entrada (fade in)
    setTimeout(() => toast.classList.remove('opacity-0'), 10);

    // Animação de saída e remoção do elemento
    setTimeout(() => {
        toast.classList.add('opacity-0');
        toast.addEventListener('transitionend', () => toast.remove());
    }, duration);
}