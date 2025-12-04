import { API_URL, showAlert } from './config.js';
import { loadDatasetsList } from './plugins/datasets.js';
import { loadModelsList } from './plugins/models/model.js';
import { loadVisualization } from './plugins/models/visualization.js';

export function switchSection(sectionName) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    const activeNav = document.querySelector(`[data-section="${sectionName}"]`);
    if (activeNav) activeNav.classList.add('active');

    // Update content
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    const activeSection = document.getElementById(`${sectionName}-section`);
    if (activeSection) activeSection.classList.add('active');

    // Load section-specific data
    if (sectionName === 'overview') refreshState();
    if (sectionName === 'datasets') loadDatasetsList();
    if (sectionName === 'models') loadModelsList();
    if (sectionName === 'visualize') loadVisualization();
}

export async function refreshState() {
    try {
        const response = await fetch(`${API_URL}/api/state`);
        const state = await response.json();
        updateOverview(state);
    } catch (error) {
        console.error('Failed to load state:', error);
    }
}

export function updateOverview(state) {
    if (!state) return;

    // Helper to safely set text content
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    };

    // Update counts in the overview cards (these match overview.html)
    setText('dataset-count', state.dataset?.exists ? '1' : '0');
    setText('model-count', state.model?.available_models?.length || '0');
    setText('training-count', '0'); // TODO: track active training jobs
    setText('prediction-count', '0'); // TODO: track predictions

    // Legacy support for old template elements (if they exist)
    setText('current-dataset', state.dataset?.path ? state.dataset.path.split('/').pop() : 'None');
    setText('dataset-status', state.dataset?.exists ? 'Ready' : 'No dataset');
    setText('current-model', state.model?.path ? state.model.path.split('/').pop() : 'None');
    setText('model-status', state.model?.exists ? 'Ready' : 'No model');
    setText('run-count', state.model?.available_runs?.length || 0);
    setText('runs-status', state.model?.available_runs?.length > 0 ? `${state.model.available_runs.length} run(s)` : 'No runs yet');
    setText('workspace-dir', state.content_dir ? state.content_dir.split('/').pop() : '');
}