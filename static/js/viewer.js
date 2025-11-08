class DatasetViewer {
    constructor(apiUrl, split = 'train') {
        this.apiUrl = apiUrl;
        this.split = split;
        this.currentIndex = 0;
        this.images = [];
        this.invertY = false;
        this.classes = {};
        this.colors = {};
        
        this.canvas = document.getElementById('viewer');
        if (!this.canvas) {
            console.warn('Canvas element with id "viewer" not found. DatasetViewer requires a canvas element.');
            return;
        }
        this.ctx = this.canvas.getContext('2d');
        
        this.setupControls();
        this.init();
    }
    
    async init() {
        // Load class info
        const classData = await fetch(`${this.apiUrl}/classes`).then(r => r.json());
        this.classes = classData.names;
        this.colors = classData.colors;
        
        // Load image list
        this.images = await fetch(`${this.apiUrl}/images/${this.split}`).then(r => r.json());
        
        if (this.images.length > 0) {
            this.loadImage(0);
        }
    }
    
    async loadImage(index) {
        this.currentIndex = index;
        const imgData = this.images[index];
        
        // Load image
        const img = new Image();
        img.src = `${this.apiUrl}/image/${this.split}/${imgData.stem}`;
        
        img.onload = async () => {
            // Resize canvas to match image
            this.canvas.width = img.width;
            this.canvas.height = img.height;
            
            // Draw image
            this.ctx.drawImage(img, 0, 0);
            
            // Load and draw labels
            const labels = await fetch(`${this.apiUrl}/labels/${this.split}/${imgData.stem}`)
                .then(r => r.json());
            
            this.drawLabels(labels, img.width, img.height);
            this.updateInfo(imgData.filename);
        };
    }
    
    drawLabels(labels, imgWidth, imgHeight) {
        labels.forEach(label => {
            const { class_id, class_name, cx, cy, w, h } = label;
            
            // Apply Y inversion if needed
            const cy_draw = this.invertY ? (1 - cy) : cy;
            
            // Convert normalized coords to pixels
            const boxW = w * imgWidth;
            const boxH = h * imgHeight;
            const x = cx * imgWidth - boxW / 2;
            const y = cy_draw * imgHeight - boxH / 2;
            
            // Get color
            const color = this.colors[class_id] || '#ff0000';
            
            // Draw box
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 2;
            this.ctx.strokeRect(x, y, boxW, boxH);
            
            // Draw label
            this.ctx.fillStyle = color;
            this.ctx.fillRect(x, Math.max(0, y - 20), this.ctx.measureText(class_name).width + 8, 20);
            this.ctx.fillStyle = 'white';
            this.ctx.font = '12px Arial';
            this.ctx.fillText(class_name, x + 4, Math.max(15, y - 5));
        });
    }
    
    setupControls() {
        document.getElementById('prev').addEventListener('click', () => {
            const newIndex = (this.currentIndex - 1 + this.images.length) % this.images.length;
            this.loadImage(newIndex);
        });
        
        document.getElementById('next').addEventListener('click', () => {
            const newIndex = (this.currentIndex + 1) % this.images.length;
            this.loadImage(newIndex);
        });
        
        document.getElementById('toggle-y').addEventListener('click', () => {
            this.invertY = !this.invertY;
            this.loadImage(this.currentIndex);
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') document.getElementById('prev').click();
            if (e.key === 'ArrowRight') document.getElementById('next').click();
            if (e.key === 'f' || e.key === 'F') document.getElementById('toggle-y').click();
        });
    }
    
    updateInfo(filename) {
        document.getElementById('info').textContent = 
            `${this.currentIndex + 1}/${this.images.length} - ${filename} (Invert Y: ${this.invertY})`;
    }
}

// Export the class for use in other modules
export { DatasetViewer };