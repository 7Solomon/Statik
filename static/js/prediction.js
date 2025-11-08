import { API_URL, showAlert } from './config.js';

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
