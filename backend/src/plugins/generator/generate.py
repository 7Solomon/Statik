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
from src.plugins.generator.image.placement import compute_placements, max_symbol_overlap
from src.plugins.generator.image.renderer import StanliRenderer
from src.plugins.generator.image.structure_generator import RandomStructureGenerator
from src.plugins.generator.image.style import random_style
from src.plugins.generator.yolo import YOLODatasetManager

class LayoutRejected(Exception):
    """No layout of this system keeps its symbols apart; skip the sample."""


class DatasetPipeline:
    """Main pipeline for generating structural engineering datasets"""
    
    def __init__(self, datasets_dir, config: DatasetConfig, status_callback=None):
        self.config = config
        self.datasets_dir = datasets_dir
        self.structure_generator = RandomStructureGenerator(
            width=config.image_size[0],
            height=config.image_size[1],
            enforce_static_determinacy=config.enforce_static_determinacy,
            archetype_weights=config.archetype_weights,
        )
        self.geometry_processor = GeometryProcessor()
        self.renderer = StanliRenderer(config)
        self.augmenter = ImageAugmenter(config)
        self.status_callback = status_callback  # Callback for progress updates
    
    def _update_status(self, current, total, message):
        """Update status via callback"""
        if self.status_callback:
            self.status_callback(current, total, message)

    def _margin_ladder(self) -> list:
        """A random fill fraction, then progressively tighter margins.

        Symbols are a fixed pixel size while node spacing scales with the frame,
        so a five-support Gerbertraeger only fits at a small margin. Shrinking
        the margin is how such a system is made to fit.
        """
        lo, hi = self.config.margin_range
        first = random.uniform(lo, hi)
        return [first] + [lo + (first - lo) * f for f in (0.55, 0.25, 0.0)]

    def build_sample(self):
        """One (image, system) pair, laid out and augmented but not yet saved.

        Only the *layout* is retried, never the system. Resampling the structure
        on rejection quietly biases the archetype mix: crowded systems fail the
        overlap check far more often than simple ones, and those crowded systems
        are exactly the multi-span beams that carry the release symbols. Doing it
        that way cut SCHUBGELENK and NORMALKRAFTGELENK to ~0.4% of instances.
        """
        system = self.structure_generator.generate()
        # One style per sample, carried on the system so the renderer and the
        # label writer measure symbols at the same stroke width.
        if self.config.randomize_appearance:
            system.style = random_style()

        best_score, structure = None, None
        for margin in self._margin_ladder():
            candidate = self.geometry_processor.normalize_coordinates(
                system,
                self.config.image_size,
                margin=margin,
                load_arrow_length_px=self.config.load_arrow_length_px,
            )
            overlap = max_symbol_overlap(
                compute_placements(candidate, self.config.load_arrow_length_px))
            in_bounds = self.geometry_processor.validate_bounds(
                candidate, self.config.image_size,
                load_arrow_length_px=self.config.load_arrow_length_px)

            # Out of frame is worse than any amount of crowding, so it costs a
            # full point and can never beat a layout that fits.
            score = overlap + (0.0 if in_bounds else 1.0)
            if best_score is None or score < best_score:
                best_score, structure = score, candidate
            if in_bounds and overlap <= self.config.max_symbol_overlap:
                break

        image = self.renderer.render_structure(structure)
        image, structure = self.augmenter.augment(image, structure)

        # Checked *after* augmentation, because that is the structure the label
        # file is written from: rotation turns every symbol and so moves its box.
        overlap = max_symbol_overlap(
            compute_placements(structure, self.config.load_arrow_length_px))
        if overlap > self.config.discard_symbol_overlap:
            raise LayoutRejected(f"symbols overlap by {overlap:.2f}")

        return image, structure
    
    def generate_dataset(self, num_samples: int) -> Path:
        print(f"Generating {num_samples} samples...")
        
        # 1. Create manager
        dataset_id = f"dataset_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        manager = YOLODatasetManager(
            self.datasets_dir,
            self.config.classes,
            dataset_id,
            load_arrow_length_px=self.config.load_arrow_length_px,
        )
        output_dir = manager.get_output_dir()
        manager.create_dataset_structure()
        
        if not (output_dir / "dataset.yaml").exists():
            raise RuntimeError("dataset.yaml not created!")
        
        train_size = int(num_samples * self.config.train_ratio)
        val_size = int(num_samples * self.config.val_ratio)
        test_size = num_samples - train_size - val_size
        
        splits = [('train', train_size), ('val', val_size), ('test', test_size)]
        sample_count = 0
        failures = 0
        rejected = 0
        
        for split_name, split_size in splits:
            for i in tqdm(range(split_size), desc=split_name):
                try:
                    image, structure = self.build_sample()
                    filename = f"{split_name}_{i:06d}_{str(uuid.uuid4())[:8]}"
                    if manager.save_sample(image, structure, filename, split_name):
                        sample_count += 1
                        self._update_status(sample_count, num_samples, f"{split_name} {i}")
                except LayoutRejected:
                    rejected += 1
                    continue
                except Exception:
                    failures += 1
                    if failures <= 5:
                        sys.stderr.write(traceback.format_exc())
                    continue
        
        print(f"Total samples SAVED: {sample_count} "
              f"({rejected} rejected for symbol overlap, {failures} failed)")
        self._report_class_histogram(manager)
        return output_dir

    def _report_class_histogram(self, manager: YOLODatasetManager):
        """A class with zero instances is a bug, so say so loudly.

        Silent empty classes are how the old class list ended up with five of
        sixteen entries that never appeared in a single label file.
        """
        histogram = manager.class_histogram()
        total = sum(histogram.values()) or 1
        print("\nClass instances:")
        for name, count in sorted(histogram.items(), key=lambda kv: -kv[1]):
            print(f"  {name:24s} {count:8d}  {100.0 * count / total:5.1f}%")

        empty = manager.empty_classes()
        if empty:
            print(f"\n[WARNING] {len(empty)} class(es) got ZERO instances: {', '.join(empty)}")
            print("          Either generate them or drop them from the class list -")
            print("          an empty class costs capacity and skews val metrics.")
        return histogram

    def preview_symbols(self):
        """Open interactive symbol gallery windows."""
        self.renderer.show_symbol_galleries()
