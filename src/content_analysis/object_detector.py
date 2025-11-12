"""Object detection using Faster R-CNN for person detection."""

import torch
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights
from PIL import Image
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ObjectDetector:
    """Object detection using Faster R-CNN ResNet50 from torchvision."""

    # COCO dataset class names (91 classes)
    COCO_CLASSES = [
        '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
        'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
        'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
        'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
        'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
        'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
        'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
        'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
        'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
        'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
        'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book',
        'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
    ]

    def __init__(self, model_name: str = "fasterrcnn_resnet50_fpn", confidence_threshold: float = 0.7):
        """Initialize object detector with Faster R-CNN.

        Args:
            model_name: Model architecture (currently only fasterrcnn_resnet50_fpn supported)
            confidence_threshold: Minimum confidence for detections (0-1)

        Raises:
            RuntimeError: If model fails to load
        """
        logger.info(f"Loading object detection model: {model_name}")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.confidence_threshold = confidence_threshold

        try:
            # Load pre-trained Faster R-CNN ResNet50 (~160MB)
            # Using new weights API for torchvision 0.13+
            try:
                weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
                self.model = fasterrcnn_resnet50_fpn(weights=weights).to(self.device)
            except AttributeError:
                # Fallback for older torchvision versions
                self.model = fasterrcnn_resnet50_fpn(pretrained=True).to(self.device)

            self.model.eval()  # Set to inference mode

            logger.info(f"Object detector loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load object detection model: {e}")
            raise RuntimeError(f"Object detection model loading failed: {e}")

    def detect(self, image: Image.Image) -> List[Dict]:
        """Detect objects in image.

        Args:
            image: PIL Image to analyze

        Returns:
            List of detection dicts with keys:
                - class: Object class name (str)
                - confidence: Detection confidence (float 0-1)
                - bbox: Bounding box [x1, y1, x2, y2] (list of floats)
        """
        try:
            # Convert PIL Image to tensor
            image_tensor = torchvision.transforms.functional.to_tensor(image).to(self.device)

            with torch.no_grad():
                predictions = self.model([image_tensor])[0]

            # Filter detections by confidence threshold
            detections = []
            for i, score in enumerate(predictions['scores']):
                if score >= self.confidence_threshold:
                    class_id = predictions['labels'][i].item()

                    # Validate class ID is in range
                    if 0 <= class_id < len(self.COCO_CLASSES):
                        class_name = self.COCO_CLASSES[class_id]

                        # Skip invalid classes
                        if class_name != 'N/A' and class_name != '__background__':
                            bbox = predictions['boxes'][i].cpu().numpy().tolist()

                            detections.append({
                                'class': class_name,
                                'confidence': float(score.item()),
                                'bbox': bbox  # [x1, y1, x2, y2]
                            })

            logger.debug(f"Detected {len(detections)} objects above threshold {self.confidence_threshold}")

            return detections

        except Exception as e:
            logger.error(f"Object detection failed: {e}", exc_info=True)
            return []

    def detect_persons_only(self, image: Image.Image) -> List[Dict]:
        """Detect only persons in image (optimized for person detection).

        Args:
            image: PIL Image to analyze

        Returns:
            List of person detection dicts
        """
        all_detections = self.detect(image)
        persons = [d for d in all_detections if d['class'] == 'person']

        logger.debug(f"Detected {len(persons)} persons")

        return persons

    def count_persons(self, image: Image.Image) -> int:
        """Count number of persons detected in image.

        Args:
            image: PIL Image to analyze

        Returns:
            Number of persons detected
        """
        persons = self.detect_persons_only(image)
        return len(persons)

    def detect_specific_classes(self, image: Image.Image, target_classes: List[str]) -> List[Dict]:
        """Detect only specific object classes.

        Args:
            image: PIL Image to analyze
            target_classes: List of class names to detect (e.g., ['person', 'car'])

        Returns:
            List of detection dicts for specified classes
        """
        all_detections = self.detect(image)
        target_set = set(target_classes)
        filtered = [d for d in all_detections if d['class'] in target_set]

        logger.debug(f"Detected {len(filtered)} objects of classes {target_classes}")

        return filtered
