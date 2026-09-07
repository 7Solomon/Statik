from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Any, Dict
from ultralytics import YOLO
import torch
from .config import VisionConfig


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float
    cx: float
    cy: float
    #: Rotation about the centre, radians, from an OBB model; 0.0 for a plain
    #: detect model. A Streckenlast is only reconstructable with this: it says
    #: which member the load lies along and how far it runs.
    angle: float = 0.0
    #: The four corners, when the model produces them.
    corners: Optional[List[tuple]] = None

@dataclass
class ImagePrediction:
    source: str
    detections: List[Detection]
    orig_width: int
    orig_height: int

class YoloPredictor:
    """Predictor with proper model path management"""
    
    def __init__(
        self,
        vision_config: VisionConfig,
        dataset_config=None,
        model_path: Optional[Union[str, Path]] = None,
        use_production_model: bool = True,
        device: Optional[str] = None
    ):
        self.vision_config = vision_config
        self.dataset_config = dataset_config
        
        # Determine model path
        if model_path is not None:
            self.model_path = Path(model_path)
        elif use_production_model:
            # Use saved production model
            self.model_path = vision_config.get_production_model_path()
        else:
            # Use latest training run
            self.model_path = vision_config.get_best_model_path()
        
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model weights not found: {self.model_path}\n"
                f"Available models: {vision_config.list_models()}\n"
                f"Available runs: {vision_config.list_runs()}"
            )
        
        print(f"Loading model from: {self.model_path}")
        
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(str(self.model_path))
        self.model.to(self.device)
        
        # Get classes
        if dataset_config and hasattr(dataset_config, 'classes'):
            self.classes = dataset_config.classes
        else:
            # Try to load from model
            self.classes = self.model.names if hasattr(self.model, 'names') else {}

    def predict(
        self,
        source: Union[str, Path, int],
        conf: float = 0.25,
        iou: float = 0.45,
        max_det: int = 1000,
        save: bool = False,
        show: bool = False,
        verbose: bool = False
    ) -> List[ImagePrediction]:
        """Run inference"""
        results = self.model.predict(
            source=str(source),
            imgsz=640,
            conf=conf,
            iou=iou,
            max_det=max_det,
            device=self.device,
            save=save,
            show=show,
            verbose=verbose,
            project=str(self.vision_config.predictions_dir) if save else None,
        )

        structured: List[ImagePrediction] = []

        for r in results:
            # An OBB model puts its predictions on `.obb`, not `.boxes`.
            container = getattr(r, "obb", None)
            oriented = container is not None
            if not oriented:
                container = getattr(r, "boxes", None)
            if container is None:
                continue

            det_list: List[Detection] = []
            if len(container) > 0:
                xyxy = container.xyxy.cpu().numpy()
                cls = container.cls.cpu().numpy()
                confs = container.conf.cpu().numpy()
                angles = container.xywhr[:, 4].cpu().numpy() if oriented else None
                quads = container.xyxyxyxy.cpu().numpy() if oriented else None

                for i in range(len(xyxy)):
                    x1, y1, x2, y2 = xyxy[i]
                    w = x2 - x1
                    h = y2 - y1
                    cx = x1 + w / 2
                    cy = y1 + h / 2
                    cid = int(cls[i])
                    cname = self.classes.get(cid, str(cid)) if isinstance(self.classes, dict) else (
                        self.classes[cid] if cid < len(self.classes) else str(cid)
                    )
                    
                    det_list.append(
                        Detection(
                            class_id=cid,
                            class_name=cname,
                            confidence=float(confs[i]),
                            x1=float(x1),
                            y1=float(y1),
                            x2=float(x2),
                            y2=float(y2),
                            width=float(w),
                            height=float(h),
                            cx=float(cx),
                            cy=float(cy),
                            angle=float(angles[i]) if angles is not None else 0.0,
                            corners=([tuple(pt) for pt in quads[i].tolist()]
                                     if quads is not None else None),
                        )
                    )

            structured.append(
                ImagePrediction(
                    source=str(r.path),
                    detections=det_list,
                    orig_width=int(getattr(r, "orig_shape", (0, 0))[1]),
                    orig_height=int(getattr(r, "orig_shape", (0, 0))[0])
                )
            )

        return structured