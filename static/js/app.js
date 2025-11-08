import { API_URL, showAlert } from './config.js';

// Import other modules
import { refreshState, updateOverview, switchSection } from './state.js';
import { loadDatasetsList, startGeneration, pollGenerationStatus, updateSplitLabels, deleteDataset } from './datasets.js';
import { loadModelsList, startTraining, pollTrainingStatus, showTrainModal, closeTrainModal, deleteModel, loadModel } from './model.js';
import { runPrediction, displayPredictionResults } from './prediction.js';
import { loadVisualization } from './visualizer.js';

// Make functions globally available for onclick handlers
window.showGenerateModal = showGenerateModal;
window.closeGenerateModal = closeGenerateModal;
window.showTrainModal = showTrainModal;
window.closeTrainModal = closeTrainModal;
window.startGeneration = startGeneration;
window.startTraining = startTraining;
window.runPrediction = runPrediction;
window.switchSection = switchSection;
window.loadVisualization = loadVisualization;
window.updateSplitLabels = updateSplitLabels;
window.deleteDataset = deleteDataset;
window.deleteModel = deleteModel;
window.loadModel = loadModel;

// Modal Management
export function showGenerateModal() {
    document.getElementById('generate-modal').classList.add('active');
}

export function closeGenerateModal() {
    document.getElementById('generate-modal').classList.remove('active');
}

// Utility - re-export for backward compatibility
export { showAlert, API_URL };

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshState();
    setInterval(refreshState, 5000);
});