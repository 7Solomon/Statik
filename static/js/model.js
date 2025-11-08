import { API_URL, showAlert } from './config.js';
import { refreshState } from './state.js';

export async function showTrainModal() {
    try {
        const response = await fetch(`${API_URL}/datasets`);
        const datasets = await response.json();
        
        if (datasets.length === 0) {
            showAlert('train-modal-alert', 'No datasets available. Please generate a dataset first.', 'warning');
            return;
        }
        
        // Populate dataset dropdown
        const select = document.getElementById('train-dataset-select');
        select.innerHTML = '<option value="">Select a dataset...</option>';
        datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.name;
            option.textContent = `${dataset.name} (${dataset.images} images)`;
            select.appendChild(option);
        });
        
        document.getElementById('train-modal').classList.add('active');
    } catch (error) {
        console.error('Failed to load datasets:', error);
        showAlert('train-modal-alert', 'Failed to load datasets', 'error');
    }
}

export function closeTrainModal() {
    document.getElementById('train-modal').classList.remove('active');
}


// Model Management
export async function loadModelsList() {
    try {
        const response = await fetch(`${API_URL}/models`);
        const models = await response.json();
        
        const listEl = document.getElementById('models-list');
        listEl.innerHTML = '';
        
        if (models.length === 0) {
            listEl.innerHTML = '<div class="list-item"><p>No models found</p></div>';
            return;
        }
        
        models.forEach(model => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <div class="item-info">
                    <h4>${model.name}</h4>
                    <p>Run: ${model.run_name || 'Unknown'} | Created: ${model.created || 'Unknown'}</p>
                </div>
                <div class="item-actions">
                    <button class="btn-small btn-danger" onclick="deleteModel('${model.name}')">Delete</button>
                </div>
            `;
            listEl.appendChild(item);
        });
    } catch (error) {
        console.error('Failed to load models:', error);
    }
}

export async function deleteModel(name) {
    if (!confirm(`Delete model "${name}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const runName = name.replace('model_', '');
        const response = await fetch(`${API_URL}/models/${runName}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('models-alert', `Model "${name}" deleted successfully`, 'success');
            loadModelsList();
            refreshState();
        } else {
            const result = await response.json();
            showAlert('models-alert', result.error || 'Failed to delete model', 'error');
        }
    } catch (error) {
        console.error('Failed to delete model:', error);
        showAlert('models-alert', 'Failed to delete model', 'error');
    }
}

export async function loadModel(name) {
    try {
        showAlert('models-alert', `Loading model "${name}"...`, 'info');
        // Add your load model logic here
        // This might involve setting the active model in the backend
    } catch (error) {
        console.error('Failed to load model:', error);
        showAlert('models-alert', 'Failed to load model', 'error');
    }
}


// Training
export async function startTraining() {
    const epochs = document.getElementById('train-epochs').value;
    const batchSize = document.getElementById('train-batch').value;
    const learningRate = document.getElementById('train-lr').value;
    const datasetName = document.getElementById('train-dataset-select').value;
    const baseModel = document.getElementById('train-base-model').value;
    const patience = document.getElementById('train-patience').value;
    const imageSize = document.getElementById('train-image-size').value;
    
    if (!datasetName) {
        showAlert('train-modal-alert', 'Please select a dataset', 'warning');
        return;
    }
    
    try {
        closeTrainModal();
        document.getElementById('training-progress-card').style.display = 'block';
        
        const response = await fetch(`${API_URL}/train`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                dataset_name: datasetName,
                epochs: parseInt(epochs),
                batch_size: parseInt(batchSize),
                learning_rate: parseFloat(learningRate),
                base_model: baseModel,
                patience: parseInt(patience),
                image_size: parseInt(imageSize)
            })
        });
        
        if (response.ok) {
            pollTrainingStatus(); // Start polling for updates
        }
    } catch (error) {
        console.error('Training failed:', error);
    }
}

export async function pollTrainingStatus() {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/train/status`);
            const status = await response.json();
            
            // Update progress bar
            document.getElementById('training-progress-fill').style.width = `${status.progress}%`;
            
            // Update text displays
            document.getElementById('train-epoch-text').textContent = 
                `Epoch ${status.current_epoch}/${status.total_epochs}`;
            document.getElementById('training-message').textContent = status.message;
            
            // Update metrics if available
            if (status.metrics) {
                document.getElementById('train-loss').textContent = 
                    status.metrics.loss.toFixed(4);
                document.getElementById('train-map').textContent = 
                    (status.metrics.map50 * 100).toFixed(2) + '%';
            }
            
            // Stop polling when training is done
            if (!status.running) {
                clearInterval(interval);
                if (status.progress === 100) {
                    document.getElementById('training-message').textContent = 'Training complete!';
                    setTimeout(() => {
                        document.getElementById('training-progress-card').style.display = 'none';
                        refreshState();
                        loadModelsList();
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('Failed to get training status:', error);
            clearInterval(interval);
        }
    }, 1000); // Poll every second
}
