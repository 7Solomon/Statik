import random
import uuid
from pathlib import Path
from tqdm import tqdm
from src.generator.config import DatasetConfig
from src.generator.geometry import GeometryProcessor
from src.generator.image.augmentation import ImageAugmenter
from src.generator.image.renderer import StanliRenderer
from src.generator.image.structure_generator import StructuralSystemGenerator
from src.generator.yolo import YOLODatasetManager

class DatasetPipeline:
    """Main pipeline for generating structural engineering datasets"""
    
    def __init__(self, config: DatasetConfig, status_callback=None):
        self.config = config
        self.structure_generator = StructuralSystemGenerator()
        self.geometry_processor = GeometryProcessor()
        self.renderer = StanliRenderer(config)
        self.augmenter = ImageAugmenter(config)
        self.dataset_manager = YOLODatasetManager(config)
        self.status_callback = status_callback  # Callback for progress updates
    
    def _update_status(self, current, total, message):
        """Update status via callback"""
        if self.status_callback:
            self.status_callback(current, total, message)
    
    def generate_dataset(self, num_samples: int):
        """Generate complete dataset with progress tracking"""
        print(f"Generating {num_samples} samples...")
        
        # Create dataset structure
        self._update_status(0, num_samples, "Creating dataset structure...")
        self.dataset_manager.create_dataset_structure()
        
        # Calculate split sizes
        train_size = int(num_samples * self.config.train_ratio)
        val_size = int(num_samples * self.config.val_ratio)
        test_size = num_samples - train_size - val_size
        
        splits = [
            ('train', train_size),
            ('val', val_size),
            ('test', test_size)
        ]
        
        sample_count = 0
        for split_name, split_size in splits:
            print(f"Generating {split_size} {split_name} samples...")
            self._update_status(
                sample_count, 
                num_samples, 
                f"Generating {split_name} split ({sample_count}/{num_samples})..."
            )
            
            for i in tqdm(range(split_size)):
                try:
                    # Generate structure
                    structure = self.structure_generator.generate_structure()
                    
                    # Normalize coordinates
                    structure = self.geometry_processor.normalize_coordinates(
                        structure, self.config.image_size
                    )
                    
                    # Render to image
                    image = self.renderer.render_structure(structure)
                    
                    # Apply augmentations
                    image, structure = self.augmenter.augment(image, structure)
                    
                    # Save to dataset
                    filename = f"{split_name}_{i:06d}_{str(uuid.uuid4())[:8]}"
                    self.dataset_manager.save_sample(image, structure, filename, split_name)
                    
                    sample_count += 1
                    
                    # Update progress every sample
                    if sample_count % 5 == 0 or sample_count == num_samples:
                        self._update_status(
                            sample_count,
                            num_samples,
                            f"Generated {sample_count}/{num_samples} samples ({split_name})..."
                        )
                        
                except Exception as e:
                    print(f"Error generating sample {i}: {e}")
                    continue
        
        self._update_status(num_samples, num_samples, "Dataset generation complete!")
        print(f"Dataset generation complete! Saved to: {self.config.output_dir}")
        print(f"Total samples: {sample_count}")
        
        return self.config.output_dir
    
    def preview_symbols(self):
        """Open interactive symbol gallery windows."""
        self.renderer.show_symbol_galleries()


#def generate_sample_dataset():
#    config = DatasetConfig()
#    
#    pipeline = DatasetPipeline(config)
#    #pipeline.generate_dataset(num_samples=5000)
#    pipeline.generate_dataset(num_samples=4)
#    return pipeline.dataset_manager
#
#def visualize_test_GALLERIES():
#    config = DatasetConfig()
#    pipeline = DatasetPipeline(config)
#    pipeline.preview_symbols()
#    return pipeline