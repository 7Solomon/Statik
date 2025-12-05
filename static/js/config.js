// Shared configuration
export const API_URL = 'http://localhost:5000';

// Utility functions
export function showAlert(elementId, message, type) {
    const alert = document.getElementById(elementId);
    if (!alert) {
        console.error(`Alert element not found: ${elementId}`);
        return;
    }
    alert.textContent = message;
    alert.className = `alert alert-${type}`;
    alert.style.display = 'block';
    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

export function togglePanel(panelName) {
    const body = document.getElementById(`body-${panelName}`);
    const arrow = document.getElementById(`arrow-${panelName}`);

    if (body.style.display === 'none') {
        body.style.display = 'block';
        arrow.classList.add('rotate-180');
    } else {
        body.style.display = 'none';
        arrow.classList.remove('rotate-180');
    }
}