import { API_URL, showAlert } from './config.js';

// Poll for generation status
let statusPollInterval = null;

export async function startGeneration() {
    const form = document.getElementById('generate-form');
    const formData = new FormData(form);
    
    const data = {
        num_samples: parseInt(formData.get('num_samples')),
        dataset_name: formData.get('dataset_name') || `dataset_${Date.now()}`
    };
    
    try {
        const response = await fetch(`${API_URL}/api/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            showAlert(error.error || 'Failed to start generation', 'error');
            return;
        }
        
        closeGenerateModal();
        showProgressModal();
        startStatusPolling();
        
    } catch (error) {
        showAlert('Error starting generation: ' + error.message, 'error');
    }
}

function showProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function closeProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function startStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    
    statusPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/api/status`);
            const status = await response.json();
            
            updateProgressUI(status);
            
            if (!status.running) {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
                
                setTimeout(() => {
                    closeProgressModal();
                    loadDatasetsList();
                }, 2000);
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 500); // Poll every 500ms for smooth updates
}

function updateProgressUI(status) {
    const progressBar = document.getElementById('generation-progress-bar');
    const progressText = document.getElementById('generation-progress-text');
    const progressMessage = document.getElementById('generation-message');
    const progressPercent = document.getElementById('generation-percent');
    
    if (progressBar) {
        const percentage = status.percentage || 0;
        progressBar.style.width = `${percentage}%`;
    }
    
    if (progressText) {
        progressText.textContent = `${status.progress || 0} / ${status.total || 0}`;
    }
    
    if (progressMessage) {
        progressMessage.textContent = status.message || 'Processing...';
    }
    
    if (progressPercent) {
        progressPercent.textContent = `${status.percentage || 0}%`;
    }
}

export async function loadDatasetsList() {
    try {
        const response = await fetch(`${API_URL}/api/datasets`);
        const datasets = await response.json();
        
        const container = document.getElementById('dataset-list');
        const emptyState = document.getElementById('empty-state');
        
        if (!container) {
            console.warn('dataset-list element not found');
            return;
        }
        
        if (datasets.length === 0) {
            container.innerHTML = '';
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }
        
        if (emptyState) emptyState.classList.add('hidden');
        
        if (container) {
            container.innerHTML = datasets.map(dataset => `
                <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 hover:shadow-md transition-all duration-200">
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex-1">
                            <h3 class="text-lg font-bold text-slate-800 mb-1">${dataset.name}</h3>
                            <p class="text-xs text-slate-500">${dataset.created}</p>
                        </div>
                        <button onclick="deleteDataset('${dataset.name}')" 
                                class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors">
                            🗑️
                        </button>
                    </div>
                    
                    <div class="grid grid-cols-3 gap-3 mb-4">
                        <div class="bg-blue-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-blue-600 mb-1">Train</p>
                            <p class="text-lg font-bold text-blue-700">${dataset.splits?.train || 0}</p>
                        </div>
                        <div class="bg-purple-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-purple-600 mb-1">Val</p>
                            <p class="text-lg font-bold text-purple-700">${dataset.splits?.val || 0}</p>
                        </div>
                        <div class="bg-green-50 rounded-lg p-3 text-center">
                            <p class="text-xs text-green-600 mb-1">Test</p>
                            <p class="text-lg font-bold text-green-700">${dataset.splits?.test || 0}</p>
                        </div>
                    </div>
                    
                    <div class="flex gap-2">
                        <button onclick="loadDataset('${dataset.name}')" 
                                class="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors text-sm">
                            Load Dataset
                        </button>
                        <button onclick="viewDataset('${dataset.name}')" 
                                class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition-colors text-sm">
                            View
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
    } catch (error) {
        console.error('Error loading datasets:', error);
        showAlert('Failed to load datasets', 'error');
    }
}

export async function deleteDataset(name) {
    if (!confirm(`Delete dataset "${name}"?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/api/datasets/${name}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Dataset deleted', 'success');
            loadDatasetsList();
        }
    } catch (error) {
        showAlert('Error deleting dataset', 'error');
    }
}

// Make functions globally available
window.deleteDataset = deleteDataset;
window.loadDataset = async (name) => {
    try {
        const response = await fetch(`${API_URL}/api/datasets/${name}/load`, {
            method: 'POST'
        });
        if (response.ok) {
            showAlert(`Loaded dataset: ${name}`, 'success');
        }
    } catch (error) {
        showAlert('Error loading dataset', 'error');
    }
};
window.viewDataset = (name) => {
    alert(`View dataset: ${name} - Feature coming soon!`);
};
