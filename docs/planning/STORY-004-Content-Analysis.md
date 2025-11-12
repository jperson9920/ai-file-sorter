# STORY-004: Python Content Analysis Module (CLIP + Faster R-CNN)

**Epic:** EPIC-001
**Story Points:** 8
**Priority:** P1 - High
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 4-5 days

## User Story

As a **user**, I want to **automatically classify images by style and detect objects** so that **the system can intelligently categorize my images as anime vs realistic, and identify images containing people**.

## Acceptance Criteria

### AC1: CLIP Style Classification
- [ ] Load OpenAI CLIP model (ViT-B/32, ~150MB)
- [ ] Implement zero-shot classification for image styles
- [ ] Support configurable style labels (anime, realistic, 3D render, etc.)
- [ ] Return confidence scores for each style
- [ ] Process images in 2-5 seconds on CPU
- [ ] Support batch processing for efficiency

### AC2: Object Detection (Person Detection)
- [ ] Load Faster R-CNN ResNet50 from torchvision (~160MB)
- [ ] Detect persons in images with bounding boxes
- [ ] Return confidence scores (threshold: 0.7)
- [ ] Support alternative models (YOLOv8n for speed)
- [ ] Handle images of any size (auto-resize)

### AC3: Model Management
- [ ] Lazy loading - defer model initialization until first use
- [ ] Cache models in configurable directory
- [ ] Auto-download models on first run
- [ ] Validate model files (checksums)
- [ ] Graceful degradation if models fail to load

### AC4: Result Format
- [ ] Return standardized result dict with:
  - `style`: detected style label
  - `style_confidence`: float 0-1
  - `style_scores`: dict of all style scores
  - `persons_detected`: int count
  - `persons_boxes`: list of bounding boxes
  - `processing_time_ms`: int
- [ ] JSON-serializable output

### AC5: Performance Optimization
- [ ] Batch process multiple images efficiently
- [ ] Use CPU inference (GPU optional)
- [ ] Image preprocessing (resize to model input size)
- [ ] Memory-efficient processing (don't load all images at once)
- [ ] Target: 1,000 images in <5 minutes

### AC6: Error Handling
- [ ] Handle corrupted/invalid images
- [ ] Handle out-of-memory errors
- [ ] Retry on transient failures
- [ ] Log detailed error context
- [ ] Continue batch processing on single failures

## Technical Implementation

### ContentAnalyzer Class

```python
# src/content_analysis/content_analyzer.py
from pathlib import Path
from typing import Dict, List, Optional
import logging
import time
from PIL import Image
import torch

from .clip_classifier import CLIPClassifier
from .object_detector import ObjectDetector
from .model_loader import ModelLoader

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Main content analysis orchestrator using CLIP and object detection."""

    def __init__(self, config: Dict):
        """Initialize content analyzer.

        Args:
            config: Configuration dict with content_analysis settings
        """
        self.config = config
        self.clip_classifier = None
        self.object_detector = None
        self.models_loaded = False

        # Model configuration
        self.models_dir = Path(config['models']['clip']['cache_dir'])
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Style classifications
        self.style_labels = [
            c['label'] for c in config['classifications']
        ]
        self.style_thresholds = {
            c['label']: c['threshold']
            for c in config['classifications']
        }

    def _ensure_models_loaded(self):
        """Lazy load models on first use."""
        if self.models_loaded:
            return

        logger.info("Loading content analysis models...")
        start = time.time()

        try:
            # Load CLIP
            self.clip_classifier = CLIPClassifier(
                model_name=self.config['models']['clip']['model_name'],
                cache_dir=str(self.models_dir)
            )

            # Load object detector
            self.object_detector = ObjectDetector(
                model_name=self.config['models']['faster_rcnn']['model_name'],
                confidence_threshold=self.config['models']['faster_rcnn']['confidence_threshold']
            )

            self.models_loaded = True
            elapsed = time.time() - start
            logger.info(f"Models loaded in {elapsed:.2f} seconds")

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise

    def analyze_image(self, image_path: Path) -> Dict:
        """Analyze a single image.

        Args:
            image_path: Path to image file

        Returns:
            Dict with analysis results
        """
        self._ensure_models_loaded()

        start_time = time.time()

        try:
            # Load image
            image = Image.open(image_path).convert('RGB')

            # Style classification with CLIP
            style_scores = self.clip_classifier.classify(image, self.style_labels)
            best_style = max(style_scores, key=style_scores.get)
            style_confidence = style_scores[best_style]

            # Object detection
            detections = self.object_detector.detect(image)
            persons = [d for d in detections if d['class'] == 'person']

            # Build result
            processing_time = (time.time() - start_time) * 1000  # ms

            result = {
                'status': 'success',
                'image_path': str(image_path),
                'style': best_style,
                'style_confidence': float(style_confidence),
                'style_scores': {k: float(v) for k, v in style_scores.items()},
                'persons_detected': len(persons),
                'persons_boxes': [
                    {
                        'bbox': p['bbox'],
                        'confidence': float(p['confidence'])
                    }
                    for p in persons
                ],
                'processing_time_ms': int(processing_time)
            }

            logger.debug(
                f"Analyzed {image_path.name}: {best_style} "
                f"({style_confidence:.2f}), {len(persons)} persons"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to analyze {image_path}: {e}")
            return {
                'status': 'error',
                'image_path': str(image_path),
                'error': str(e)
            }

    def analyze_batch(
        self,
        image_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """Analyze multiple images.

        Args:
            image_paths: List of image paths
            progress_callback: Optional callback(current, total)

        Returns:
            List of result dicts
        """
        self._ensure_models_loaded()

        results = []
        total = len(image_paths)

        logger.info(f"Analyzing {total} images...")

        for idx, image_path in enumerate(image_paths, 1):
            result = self.analyze_image(image_path)
            results.append(result)

            if progress_callback:
                progress_callback(idx, total)

            # Log progress every 100 images
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")

        # Summary statistics
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = total - successful

        logger.info(
            f"Batch analysis complete: {successful} success, {failed} failed"
        )

        return results

    def get_category_suggestion(self, analysis_result: Dict) -> str:
        """Suggest a category based on analysis results.

        Args:
            analysis_result: Result from analyze_image()

        Returns:
            Suggested category name
        """
        if analysis_result['status'] != 'success':
            return 'Uncategorized'

        style = analysis_result['style']
        confidence = analysis_result['style_confidence']
        persons_count = analysis_result['persons_detected']

        # High-confidence anime with persons
        if style == 'anime style illustration' and confidence > 0.7:
            if persons_count > 0:
                return 'Anime/Characters'
            else:
                return 'Anime/Scenery'

        # High-confidence realistic photos
        elif style == 'realistic photograph' and confidence > 0.7:
            if persons_count > 0:
                return 'Photos/People'
            else:
                return 'Photos/Other'

        # 3D renders
        elif style == '3D render' and confidence > 0.6:
            return '3D/Renders'

        # Low confidence - uncertain
        else:
            return 'Uncategorized'
```

### CLIP Classifier

```python
# src/content_analysis/clip_classifier.py
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CLIPClassifier:
    """Zero-shot image classification using CLIP."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", cache_dir: str = None):
        """Initialize CLIP model.

        Args:
            model_name: HuggingFace model identifier
            cache_dir: Directory to cache downloaded models
        """
        logger.info(f"Loading CLIP model: {model_name}")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        self.processor = CLIPProcessor.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )

        self.model = CLIPModel.from_pretrained(
            model_name,
            cache_dir=cache_dir
        ).to(self.device)

        self.model.eval()  # Inference mode

    def classify(self, image: Image.Image, labels: List[str]) -> Dict[str, float]:
        """Classify image against candidate labels.

        Args:
            image: PIL Image
            labels: List of text labels to classify against

        Returns:
            Dict mapping labels to confidence scores (0-1)
        """
        with torch.no_grad():
            # Prepare inputs
            inputs = self.processor(
                text=labels,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # Get predictions
            outputs = self.model(**inputs)

            # Calculate probabilities
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)[0]

            # Build result dict
            scores = {
                label: prob.item()
                for label, prob in zip(labels, probs)
            }

            return scores

    def classify_batch(
        self,
        images: List[Image.Image],
        labels: List[str]
    ) -> List[Dict[str, float]]:
        """Classify multiple images efficiently.

        Args:
            images: List of PIL Images
            labels: List of text labels

        Returns:
            List of score dicts
        """
        with torch.no_grad():
            inputs = self.processor(
                text=labels,
                images=images,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)

            results = []
            for image_probs in probs:
                scores = {
                    label: prob.item()
                    for label, prob in zip(labels, image_probs)
                }
                results.append(scores)

            return results
```

### Object Detector

```python
# src/content_analysis/object_detector.py
import torch
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from PIL import Image
import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ObjectDetector:
    """Object detection using Faster R-CNN."""

    # COCO dataset class names
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
        """Initialize object detector.

        Args:
            model_name: Model to use
            confidence_threshold: Minimum confidence for detections
        """
        logger.info(f"Loading object detection model: {model_name}")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.confidence_threshold = confidence_threshold

        # Load pre-trained model
        self.model = fasterrcnn_resnet50_fpn(pretrained=True).to(self.device)
        self.model.eval()

    def detect(self, image: Image.Image) -> List[Dict]:
        """Detect objects in image.

        Args:
            image: PIL Image

        Returns:
            List of detection dicts with 'class', 'confidence', 'bbox'
        """
        # Convert to tensor
        image_tensor = torchvision.transforms.functional.to_tensor(image).to(self.device)

        with torch.no_grad():
            predictions = self.model([image_tensor])[0]

        # Filter by confidence threshold
        detections = []
        for i, score in enumerate(predictions['scores']):
            if score >= self.confidence_threshold:
                class_id = predictions['labels'][i].item()
                class_name = self.COCO_CLASSES[class_id]

                if class_name != 'N/A':
                    bbox = predictions['boxes'][i].cpu().numpy().tolist()

                    detections.append({
                        'class': class_name,
                        'confidence': score.item(),
                        'bbox': bbox  # [x1, y1, x2, y2]
                    })

        return detections

    def detect_persons_only(self, image: Image.Image) -> List[Dict]:
        """Detect only persons in image (optimized).

        Args:
            image: PIL Image

        Returns:
            List of person detection dicts
        """
        all_detections = self.detect(image)
        return [d for d in all_detections if d['class'] == 'person']
```

## Testing Strategy

### Unit Tests

```python
# tests/test_content_analysis/test_clip_classifier.py
def test_clip_classification():
    classifier = CLIPClassifier()

    # Create test image (blue square)
    image = Image.new('RGB', (224, 224), color='blue')

    labels = ["anime style illustration", "realistic photograph", "3D render"]
    scores = classifier.classify(image, labels)

    # Verify scores sum to ~1.0
    assert abs(sum(scores.values()) - 1.0) < 0.01

    # Verify all labels present
    for label in labels:
        assert label in scores
        assert 0 <= scores[label] <= 1

# tests/test_content_analysis/test_object_detector.py
def test_person_detection():
    detector = ObjectDetector(confidence_threshold=0.5)

    # Load test image with person
    image = Image.open('tests/fixtures/person.jpg')

    detections = detector.detect_persons_only(image)

    # Verify detection format
    assert isinstance(detections, list)
    if len(detections) > 0:
        assert 'class' in detections[0]
        assert 'confidence' in detections[0]
        assert 'bbox' in detections[0]
        assert detections[0]['class'] == 'person'
```

### Integration Tests

```python
# tests/test_content_analysis/test_integration.py
def test_analyze_anime_image():
    config = load_test_config()
    analyzer = ContentAnalyzer(config)

    # Test with known anime image
    result = analyzer.analyze_image(Path('tests/fixtures/anime_sample.jpg'))

    assert result['status'] == 'success'
    assert 'style' in result
    assert 'style_confidence' in result
    assert 'persons_detected' in result
    assert result['processing_time_ms'] > 0

def test_category_suggestion():
    config = load_test_config()
    analyzer = ContentAnalyzer(config)

    # Mock analysis result
    result = {
        'status': 'success',
        'style': 'anime style illustration',
        'style_confidence': 0.85,
        'persons_detected': 2
    }

    category = analyzer.get_category_suggestion(result)
    assert category == 'Anime/Characters'
```

### Performance Tests

```python
def test_batch_performance():
    """Verify 1,000 images in <5 minutes."""
    config = load_test_config()
    analyzer = ContentAnalyzer(config)

    # Generate 100 test images (scaled down for test)
    test_images = [
        Path(f'tests/fixtures/test_{i}.jpg')
        for i in range(100)
    ]

    import time
    start = time.time()

    results = analyzer.analyze_batch(test_images)

    elapsed = time.time() - start

    assert len(results) == 100
    assert elapsed < 30  # 100 images in <30 seconds = 1000 in <5 minutes
```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests pass with 85%+ coverage
- [ ] Integration tests with real images pass
- [ ] Performance test: 1,000 images in <5 minutes
- [ ] Models auto-download on first run
- [ ] Graceful handling of GPU/CPU selection
- [ ] Error handling for all edge cases
- [ ] Configuration options documented
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-001 (Project setup for configuration)

**Blocks:**
- STORY-005 (Preference learning uses content analysis)
- STORY-008 (Workflow orchestration uses content analysis)

## Notes

- CLIP model is ~150MB, Faster R-CNN is ~160MB
- First run will download models (may take 5-10 minutes)
- CPU inference is sufficient but slower than GPU
- Consider YOLOv8n (6MB) as faster alternative to Faster R-CNN
- PyTorch installation includes large dependencies (~2GB)

## Risks

- **Medium Risk:** Model inference may be slow on older CPUs
  - *Mitigation:* Batch processing, optional GPU support, smaller models

- **Medium Risk:** Model download may fail on restricted networks
  - *Mitigation:* Manual download instructions, offline model support

- **Low Risk:** Out-of-memory errors on large images
  - *Mitigation:* Resize images before processing, error handling

## Related Files

- `/src/content_analysis/content_analyzer.py`
- `/src/content_analysis/clip_classifier.py`
- `/src/content_analysis/object_detector.py`
- `/src/content_analysis/model_loader.py`
- `/tests/test_content_analysis/`
- `/data/models/` (model cache directory)

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
