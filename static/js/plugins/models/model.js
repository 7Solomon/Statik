import { refreshState } from '../../state.js';
import { API_URL, showAlert } from '../../config.js';


export async function initModels() {
    loadModelsList();
    if (typeof pollTrainingStatus === 'function') pollTrainingStatus();
    loadVisualization();
    if (typeof loadPredictionModels === 'function') {
        loadPredictionModels();
    } else {
        loadModelsList();
    }

    // Attach the event listener to the new form
    const predForm = document.getElementById('prediction-form');
    if (predForm) {
        predForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await runPrediction(); // Call your existing imported function
        });
    }
}

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
        const response = await fetch(`${API_URL}/api/models`);
        const models = await response.json();

        const listEl = document.getElementById('model-list');
        if (!listEl) {
            console.warn('model-list element not found');
            return;
        }

        listEl.innerHTML = '';

        if (models.length === 0) {
            listEl.innerHTML = '<div class="text-center py-8 text-slate-500">No models found</div>';
            return;
        }

        models.forEach(model => {
            const item = document.createElement('div');
            item.className = 'bg-white rounded-2xl p-6 shadow-sm border border-slate-200';
            item.innerHTML = `
                <div class="flex items-start justify-between mb-4">
                    <div class="flex-1">
                        <h3 class="text-lg font-bold text-slate-800 mb-1">${model.name}</h3>
                        <p class="text-xs text-slate-500">Run: ${model.run_name || 'Unknown'} | Created: ${model.created || 'Unknown'}</p>
                    </div>
                    <button onclick="deleteModel('${model.run_name}')" 
                            class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors">
                        🗑️
                    </button>
                </div>
                <div class="flex gap-2">
                    <button onclick="loadModel('${model.run_name}')" 
                            class="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors text-sm">
                        Load Model
                    </button>
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
            headers: { 'Content-Type': 'application/json' },
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


// Prediction
export async function runPrediction() {
    const fileInput = document.getElementById('predict-image');
    const conf = document.getElementById('predict-conf').value;
    const iou = document.getElementById('predict-iou').value;

    if (!fileInput.files[0]) {
        showAlert('predict-alert', 'Please select an image', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('image', fileInput.files[0]);

    try {
        const response = await fetch(`${API_URL}/predict?conf=${conf}&iou=${iou}`, {
            method: 'POST',
            body: formData
        });

        const results = await response.json();

        if (response.ok) {
            displayPredictionResults(results, fileInput.files[0]);
        } else {
            showAlert('predict-alert', results.error, 'error');
        }
    } catch (error) {
        showAlert('predict-alert', 'Prediction failed: ' + error.message, 'error');
    }
}

export function displayPredictionResults(results, imageFile) {
    const container = document.getElementById('prediction-results');
    container.style.display = 'block';

    // Draw image with detections
    const canvas = document.getElementById('prediction-canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);

        // Draw detections
        if (results[0] && results[0].detections) {
            results[0].detections.forEach(det => {
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 2;
                ctx.strokeRect(det.x1, det.y1, det.width, det.height);

                ctx.fillStyle = '#00ff00';
                ctx.fillRect(det.x1, det.y1 - 20, 150, 20);
                ctx.fillStyle = 'black';
                ctx.font = '14px Arial';
                ctx.fillText(`${det.class_name} ${(det.confidence * 100).toFixed(1)}%`, det.x1 + 5, det.y1 - 5);
            });

            // Show detections list
            const detList = document.getElementById('detections-list');
            detList.innerHTML = '<h4>Detections:</h4>';
            results[0].detections.forEach(det => {
                const item = document.createElement('div');
                item.className = 'detection-item';
                item.innerHTML = `
                    <span class="class-name">${det.class_name}</span>
                    <span class="confidence">${(det.confidence * 100).toFixed(1)}%</span>
                `;
                detList.appendChild(item);
            });
        }
    };

    img.src = URL.createObjectURL(imageFile);
}
