// static/js/components/dropdown.js
function toggleMenu() {
    const menu = document.getElementById('cadastros-menu-items');
    if (menu) menu.classList.toggle('hidden');
}

window.addEventListener('click', function(e) {
    const menuContainer = document.getElementById('cadastros-menu');
    if (menuContainer && !menuContainer.contains(e.target)) {
        document.getElementById('cadastros-menu-items').classList.add('hidden');
    }
});