// Shared configuration
export const API_URL = 'http://localhost:5000/api';

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
