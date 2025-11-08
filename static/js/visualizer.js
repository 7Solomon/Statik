import { API_URL } from './config.js';

// Visualization
export function loadVisualization() {
    const split = document.getElementById('viz-split').value;
    if (window.viewer) {
        window.viewer.loadSplit(split);
    } else {
        window.viewer = new DatasetViewer(API_URL, split);
    }
}