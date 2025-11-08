import { API_URL } from './config.js';
import { DatasetViewer } from './viewer.js';

// Visualization
export function loadVisualization() {
    // Check if this is the dataset viewer page (has canvas with id 'viewer')
    // or just a generic visualization page
    const viewerCanvas = document.getElementById('viewer');
    
    if (!viewerCanvas) {
        // This is not the dataset viewer page, just a visualization page
        console.log('Visualization page loaded (no dataset viewer canvas)');
        return;
    }
    
    // This is the dataset viewer page, initialize the viewer
    const splitEl = document.getElementById('viz-split');
    const split = splitEl ? splitEl.value : 'train'; // Default to 'train' if element not found
    
    if (window.viewer) {
        window.viewer.loadSplit(split);
    } else {
        window.viewer = new DatasetViewer(API_URL, split);
    }
}