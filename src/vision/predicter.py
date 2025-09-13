from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Any, Dict

from ultralytics import YOLO
import torch


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

@dataclass
class ImagePrediction:
    source: str
    detections: List[Detection]
    orig_width: int
    orig_height: int

class YoloPredictor:
    """
    Predictor for a trained YOLOv8 model produced by YOLOTrainer.
    Expects config with: output_dir, image_size, classes
    """
    def __init__(
                self, config,
                model_path: Optional[Union[str, Path]] = None,
                device: Optional[str] = None
            ):
        self.config = config
        if model_path is None:
            model_path = Path(config.output_dir) / ".." / "runs" / "detect" / "structural_detection_v1" / "weights" / "best.pt"
        
        
        self.model_path = Path(model_path).resolve()
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model weights not found: {self.model_path}")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(str(self.model_path))
        self.model.to(self.device)

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
        """
        Run inference on:
          - image file
          - directory
          - glob pattern
          - video file
          - webcam index (int)

        Returns structured predictions (only for image-like sources; for video/webcam
        you typically rely on saved results).
        """
        results = self.model.predict(
            source=str(source),
            imgsz=self.config.image_size[0],
            conf=conf,
            iou=iou,
            max_det=max_det,
            device=self.device,
            save=save,
            show=show,
            verbose=verbose
        )

        structured: List[ImagePrediction] = []
        classes = getattr(self.config, "classes", None)

        for r in results:
            # Skip frames without standard attributes (rare edge cases) maybe change in here!!!
            if not hasattr(r, "boxes"):
                continue

            det_list: List[Detection] = []
            if r.boxes is not None and len(r.boxes) > 0:
                xyxy = r.boxes.xyxy.cpu().numpy()
                cls = r.boxes.cls.cpu().numpy()
                confs = r.boxes.conf.cpu().numpy()
                for i in range(len(xyxy)):
                    x1, y1, x2, y2 = xyxy[i]
                    w = x2 - x1
                    h = y2 - y1
                    cx = x1 + w / 2
                    cy = y1 + h / 2
                    cid = int(cls[i])
                    cname = classes[cid] if classes and cid < len(classes) else str(cid)
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
                            cy=float(cy)
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

    def predict_as_dicts(
        self,
        source: Union[str, Path, int],
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Helper that converts ImagePrediction objects into plain dicts (JSON-friendly)."""
        out = []
        for p in self.predict(source, **kwargs):
            out.append({
                "source": p.source,
                "orig_width": p.orig_width,
                "orig_height": p.orig_height,
                "detections": [
                    {
                        "class_id": d.class_id,
                        "class_name": d.class_name,
                        "confidence": d.confidence,
                        "x1": d.x1,
                        "y1": d.y1,
                        "x2": d.x2,
                        "y2": d.y2,
                        "width": d.width,
                        "height": d.height,
                        "cx": d.cx,
                        "cy": d.cy
                    }
                    for d in p.detections
                ]
            })
        return out


def load_default_predictor(config) -> YoloPredictor:
    """Convenience loader using default training path."""
    return YoloPredictor(config)