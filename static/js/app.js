import { API_URL, showAlert, togglePanel } from './config.js';
import { refreshState, updateOverview, switchSection } from './state.js';
import { loadDatasetsList, startGeneration, deleteDataset } from './plugins/datasets.js';
import { loadModelsList, startTraining, pollTrainingStatus, showTrainModal, closeTrainModal, deleteModel, loadModel, runPrediction, initModels } from './plugins/models/model.js';
import { loadVisualization } from './plugins/models/visualization.js';
import { initLabeler, triggerRender } from './plugins/labeler/interaction/handeler.js';
import { runAnalysis } from './plugins/labeler/analysisHandler.js'


// ---------------------
// Template loading function
async function loadTemplate(name) {
    try {
        const response = await fetch(`/static/templates/${name}.html`);
        if (!response.ok) throw new Error(`Failed to load ${name}`);
        return await response.text();
    } catch (error) {
        console.error(`Error loading template ${name}:`, error);
        return `<div class="p-4 text-red-600">Error loading ${name}</div>`;
    }
}
async function loadComponent(id, url) {
    const el = document.getElementById(id);
    if (!el) {
        console.error(`Element #${id} not found.`);
        return;
    }
    const response = await fetch(url);
    const html = await response.text();
    el.innerHTML = html;
}
async function loadModals() {
    try {
        const [singleLoadHtml, distLoadHtml] = await Promise.all([
            fetch('/static/templates/components/single_load_modal.html').then(r => r.text()),
            fetch('/static/templates/components/distributed_load_modal.html').then(r => r.text())
        ]);

        document.getElementById('single_load_modal').innerHTML = singleLoadHtml;
        document.getElementById('distributed_load_modal').innerHTML = distLoadHtml;
    } catch (err) {
        console.error("Failed to load modal templates:", err);
    }
}

// Load sidebar and modals (these are persistent)
async function initializeApp() {
    // Load sidebar
    await loadComponent("sidebar", "/static/templates/components/sidebar.html");

    loadModals();

    // Setup navigation
    setupNavigation();

    // Load default page (overview)
    await loadPage('overview');
}

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const href = link.getAttribute('href');
            const page = href.replace('#', '');

            // Update active state with Tailwind classes
            document.querySelectorAll('.nav-item').forEach(l => {
                l.classList.remove('bg-blue-50', 'text-blue-600', 'active');
                l.classList.add('text-slate-600');
            });
            link.classList.remove('text-slate-600');
            link.classList.add('bg-blue-50', 'text-blue-600', 'active');

            // Load page
            await loadPage(page);
        });
    });
}

// Load page content
async function loadPage(pageName) {
    const mainContent = document.getElementById('main-content');
    mainContent.innerHTML = '<div class="text-center py-8">Loading...</div>';

    const templatePaths = {
        'overview': 'overview',
        'datasets': 'plugins/datasets',
        'models': 'plugins/models',
        'labeler': 'plugins/labeler'
    };

    // Use the mapped path, or default to the pageName if not listed
    const path = templatePaths[pageName] || pageName;

    const content = await loadTemplate(path);
    mainContent.innerHTML = content;

    // Wait for DOM to update before calling page-specific initialization
    // Use setTimeout(0) to defer execution until after DOM updates
    setTimeout(() => {
        switch (pageName) {
            case 'overview':
                refreshState();
                break;
            case 'datasets':
                loadDatasetsList();
                break;
            case 'models':
                initModels();
                break;
            case 'labeler':
                initLabeler();
                break;
        }
    }, 0);
}

// Modal Management
function openModal(modalName) {
    const modal = document.getElementById(`${modalName}-modal`);
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function closeModal(modalName) {
    const modal = document.getElementById(`${modalName}-modal`);
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

// Make functions globally available
window.openModal = openModal;
window.closeModal = closeModal;
window.showTrainModal = showTrainModal;
window.closeTrainModal = closeTrainModal;
window.startGeneration = startGeneration;
window.startTraining = startTraining;
window.runPrediction = runPrediction;
window.switchSection = switchSection;
window.loadVisualization = loadVisualization;
window.deleteDataset = deleteDataset;
window.deleteModel = deleteModel;
window.loadModel = loadModel;
window.togglePanel = togglePanel;
window.runAnalysis = runAnalysis;
window.triggerRender = triggerRender;


// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    await initializeApp();
    refreshState();
    setInterval(refreshState, 5000);
});
