import { API_URL, showAlert } from './config.js';
import { loadDatasetsList } from './datasets.js';
import { loadModelsList } from './model.js';
import { loadVisualization } from './visualizer.js';

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const section = item.dataset.section;
        switchSection(section);
    });
});

export function switchSection(sectionName) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');
    
    // Update content
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${sectionName}-section`).classList.add('active');
    
    // Load section-specific data
    if (sectionName === 'overview') refreshState();
    if (sectionName === 'datasets') loadDatasetsList();
    if (sectionName === 'models') loadModelsList();
    if (sectionName === 'visualize') loadVisualization();
}

export async function refreshState() {
    try {
        const response = await fetch(`${API_URL}/state`);
        const state = await response.json();
        updateOverview(state);
    } catch (error) {
        console.error('Failed to load state:', error);
    }
}

export function updateOverview(state) {
    // Dataset info
    document.getElementById('current-dataset').textContent = 
        state.dataset.path ? state.dataset.path.split('/').pop() : 'None';
    document.getElementById('dataset-status').textContent = 
        state.dataset.exists ? 'Ready' : 'No dataset';
    
    // Model info
    document.getElementById('current-model').textContent = 
        state.model.path ? state.model.path.split('/').pop() : 'None';
    document.getElementById('model-status').textContent = 
        state.model.exists ? 'Ready' : 'No model';
    
    // Runs info
    document.getElementById('run-count').textContent = state.model.available_runs.length;
    document.getElementById('runs-status').textContent = 
        state.model.available_runs.length > 0 ? `${state.model.available_runs.length} run(s)` : 'No runs yet';
    
    // Workspace
    document.getElementById('workspace-dir').textContent = 
        state.content_dir.split('/').pop();
}