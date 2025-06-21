// static/js/components/dropdown.js
function toggleMenu(menuId) {
    // Close all other dropdowns
    document.querySelectorAll('[id$="-menu-items"]').forEach(menu => {
        if (menu.id !== menuId) {
            menu.classList.add('hidden');
        }
    });

    // Toggle the clicked dropdown
    const menu = document.getElementById(menuId);
    if (menu) menu.classList.toggle('hidden');    
}

window.addEventListener('click', function(e) {
    document.querySelectorAll('[id$="-menu"]').forEach(container => {
        if (container && !container.contains(e.target)) {
            container.querySelector('[id$="-menu-items"]').classList.add('hidden');
        }
    });
});
