import { API_URL, showAlert } from './config.js';
import { refreshState } from './state.js';

// Update split labels dynamically
export function updateSplitLabels() {
    const train = parseInt(document.getElementById('train-split').value);
    const val = parseInt(document.getElementById('val-split').value);
    const test = parseInt(document.getElementById('test-split').value);
    
    const total = train + val + test;
    if (total !== 100) {
        // Auto-adjust test to make it 100%
        document.getElementById('test-split').value = 100 - train - val;
    }
    
    document.getElementById('train-split-val').textContent = train + '%';
    document.getElementById('val-split-val').textContent = val + '%';
    document.getElementById('test-split-val').textContent = document.getElementById('test-split').value + '%';
}

// Dataset Management
export async function loadDatasetsList() {
    try {
        const response = await fetch(`${API_URL}/datasets`);
        const datasets = await response.json();
        
        const listEl = document.getElementById('datasets-list');
        listEl.innerHTML = '';
        
        if (datasets.length === 0) {
            listEl.innerHTML = '<div class="list-item"><p>No datasets found</p></div>';
            return;
        }
        
        datasets.forEach(dataset => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <div class="item-info">
                    <h4>${dataset.name}</h4>
                    <p>${dataset.images} images | Created: ${dataset.created}</p>
                </div>
                <div class="item-actions">
                    <button class="btn-small btn-danger" onclick="deleteDataset('${dataset.name}')">Delete</button>
                </div>
            `;
            listEl.appendChild(item);
        });
    } catch (error) {
        console.error('Failed to load datasets:', error);
    }
}

export async function deleteDataset(name) {
    if (!confirm(`Delete dataset "${name}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/datasets/${name}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('datasets-alert', `Dataset "${name}" deleted successfully`, 'success');
            loadDatasetsList();
            refreshState();
        } else {
            const result = await response.json();
            showAlert('datasets-alert', result.error || 'Failed to delete dataset', 'error');
        }
    } catch (error) {
        console.error('Failed to delete dataset:', error);
        showAlert('datasets-alert', 'Failed to delete dataset', 'error');
    }
}


// Generation
export async function startGeneration() {
    const numSamples = document.getElementById('gen-num-samples').value;
    const datasetName = document.getElementById('gen-dataset-name').value;
    
    try {
        const response = await fetch(`${API_URL}/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                num_samples: parseInt(numSamples),
                dataset_name: datasetName || null
            })
        });
        
        if (response.ok) {
            const { closeGenerateModal } = await import('./app.js');
            closeGenerateModal();
            document.getElementById('generation-progress-card').style.display = 'block';
            pollGenerationStatus();
        }
    } catch (error) {
        console.error('Generation failed:', error);
    }
}

export async function pollGenerationStatus() {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/status`);
            const status = await response.json();
            
            const progress = (status.progress / status.total) * 100;
            document.getElementById('generation-progress-fill').style.width = `${progress}%`;
            document.getElementById('gen-progress-text').textContent = `${status.progress} / ${status.total}`;
            document.getElementById('gen-status-text').textContent = status.status || 'Processing...';
            document.getElementById('gen-split-text').textContent = status.current_split || '-';
            document.getElementById('generation-message').textContent = status.message;
            
            if (!status.running) {
                clearInterval(interval);
                if (status.progress === status.total) {
                    setTimeout(() => {
                        document.getElementById('generation-progress-card').style.display = 'none';
                        refreshState();
                        loadDatasetsList();
                    }, 2000);
                }
            }
        } catch (error) {
            clearInterval(interval);
        }
    }, 1000);
}

