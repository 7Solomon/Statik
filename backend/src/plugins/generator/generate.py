import random
import sys
import time
import traceback
import uuid
from pathlib import Path
from tqdm import tqdm
from src.plugins.generator.config import DatasetConfig
from src.plugins.generator.geometry import GeometryProcessor
from src.plugins.generator.image.augmentation import ImageAugmenter
from src.plugins.generator.image.renderer import StanliRenderer
#from src.plugins.generator.image.structure_generator import StructuralSystemGenerator
from src.plugins.generator.image.structure_generator import RandomStructureGenerator
from src.plugins.generator.yolo import YOLODatasetManager

class DatasetPipeline:
    """Main pipeline for generating structural engineering datasets"""
    
    def __init__(self, datasets_dir, config: DatasetConfig, status_callback=None):
        self.config = config
        self.datasets_dir = datasets_dir
        self.structure_generator = RandomStructureGenerator()
        self.geometry_processor = GeometryProcessor()
        self.renderer = StanliRenderer(config)
        self.augmenter = ImageAugmenter(config)
        #self.dataset_manager = YOLODatasetManager(datasets_dir, config.classes)
        self.status_callback = status_callback  # Callback for progress updates
    
    def _update_status(self, current, total, message):
        """Update status via callback"""
        if self.status_callback:
            self.status_callback(current, total, message)
    
    def generate_dataset(self, num_samples: int) -> Path:
        print(f"Generating {num_samples} samples...")
        
        # 1. Create manager
        dataset_id = f"dataset_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        manager = YOLODatasetManager(self.datasets_dir, self.config.classes, dataset_id)
        output_dir = manager.get_output_dir()
        
        #print(f"[PIPELINE] Output: {output_dir}")
        
        #print("[PIPELINE] Creating dataset structure...")
        manager.create_dataset_structure()
        
        if not (output_dir / "dataset.yaml").exists():
            raise RuntimeError("dataset.yaml not created!")
        
        train_size = int(num_samples * self.config.train_ratio)
        val_size = int(num_samples * self.config.val_ratio)
        test_size = num_samples - train_size - val_size
        
        splits = [('train', train_size), ('val', val_size), ('test', test_size)]
        sample_count = 0
        
        for split_name, split_size in splits:
            #print(f"Generating {split_size} {split_name} samples...")
            
            for i in tqdm(range(split_size)):
                try:
                    system = self.structure_generator.generate()
                    structure = self.geometry_processor.normalize_coordinates(system, self.config.image_size)
                    image = self.renderer.render_structure(structure)
                    image, structure = self.augmenter.augment(image, structure)
                    
                    filename = f"{split_name}_{i:06d}_{str(uuid.uuid4())[:8]}"
                    
                    if manager.save_sample(image, structure, filename, split_name):
                        sample_count += 1
                        
                except Exception as e:
                    sys.stderr.write(traceback.format_exc())
                    print(f"Error generating sample {i}: {e}")
                    continue
        
        print(f"Total samples SAVED: {sample_count}")
        return output_dir

            
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