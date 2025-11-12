"""Main content analysis orchestrator combining CLIP and object detection."""

from pathlib import Path
from typing import Dict, List, Optional
import logging
import time
from PIL import Image

from .clip_classifier import CLIPClassifier
from .object_detector import ObjectDetector

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Main content analysis orchestrator using CLIP for style and Faster R-CNN for objects."""

    def __init__(self, config: Dict):
        """Initialize content analyzer with configuration.

        Args:
            config: Configuration dict with content_analysis settings:
                - enabled: bool
                - models: dict with clip and faster_rcnn settings
                - classifications: list of style labels and thresholds
        """
        self.config = config.get('content_analysis', {})
        self.enabled = self.config.get('enabled', True)

        self.clip_classifier = None
        self.object_detector = None
        self.models_loaded = False

        if not self.enabled:
            logger.info("Content analysis disabled in configuration")
            return

        # Model configuration
        models_config = self.config.get('models', {})
        clip_config = models_config.get('clip', {})

        self.models_dir = Path(clip_config.get('cache_dir', 'data/models'))
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Style classifications from config
        classifications = self.config.get('classifications', [])
        if classifications:
            self.style_labels = [c['label'] for c in classifications]
            self.style_thresholds = {c['label']: c['threshold'] for c in classifications}
        else:
            # Default classifications
            self.style_labels = [
                "anime style illustration",
                "realistic photograph",
                "3D render"
            ]
            self.style_thresholds = {
                "anime style illustration": 0.6,
                "realistic photograph": 0.6,
                "3D render": 0.5
            }

        logger.info(f"ContentAnalyzer initialized (enabled={self.enabled})")

    def _ensure_models_loaded(self):
        """Lazy load models on first use."""
        if self.models_loaded:
            return

        if not self.enabled:
            raise RuntimeError("Content analysis is disabled in configuration")

        logger.info("Loading content analysis models...")
        start = time.time()

        try:
            # Load CLIP classifier
            clip_config = self.config.get('models', {}).get('clip', {})
            model_name = clip_config.get('model_name', 'openai/clip-vit-base-patch32')

            self.clip_classifier = CLIPClassifier(
                model_name=model_name,
                cache_dir=str(self.models_dir)
            )

            # Load object detector
            rcnn_config = self.config.get('models', {}).get('faster_rcnn', {})
            model_name = rcnn_config.get('model_name', 'fasterrcnn_resnet50_fpn')
            confidence = rcnn_config.get('confidence_threshold', 0.7)

            self.object_detector = ObjectDetector(
                model_name=model_name,
                confidence_threshold=confidence
            )

            self.models_loaded = True
            elapsed = time.time() - start
            logger.info(f"Models loaded successfully in {elapsed:.2f} seconds")

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise

    def analyze_image(self, image_path: Path) -> Dict:
        """Analyze a single image for style and content.

        Args:
            image_path: Path to image file

        Returns:
            Dict with analysis results:
                - status: 'success' or 'error'
                - image_path: str path
                - style: detected style label
                - style_confidence: float 0-1
                - style_scores: dict of all style scores
                - persons_detected: int count
                - persons_boxes: list of person bounding boxes
                - processing_time_ms: int milliseconds
                - error: str (if status is 'error')
        """
        if not self.enabled:
            return {
                'status': 'disabled',
                'image_path': str(image_path),
                'error': 'Content analysis is disabled'
            }

        self._ensure_models_loaded()

        start_time = time.time()

        try:
            # Load image
            image = Image.open(image_path).convert('RGB')

            # Style classification with CLIP
            style_scores = self.clip_classifier.classify(image, self.style_labels)
            best_style = max(style_scores, key=style_scores.get)
            style_confidence = style_scores[best_style]

            # Object detection for persons
            detections = self.object_detector.detect_persons_only(image)
            persons_count = len(detections)

            # Build result
            processing_time = (time.time() - start_time) * 1000  # milliseconds

            result = {
                'status': 'success',
                'image_path': str(image_path),
                'style': best_style,
                'style_confidence': float(style_confidence),
                'style_scores': {k: float(v) for k, v in style_scores.items()},
                'persons_detected': persons_count,
                'persons_boxes': [
                    {
                        'bbox': p['bbox'],
                        'confidence': float(p['confidence'])
                    }
                    for p in detections
                ],
                'all_objects': [],  # Can be populated if needed
                'processing_time_ms': int(processing_time)
            }

            logger.debug(
                f"Analyzed {image_path.name}: {best_style} "
                f"({style_confidence:.2f}), {persons_count} persons, {processing_time:.0f}ms"
            )

            return result

        except FileNotFoundError:
            logger.error(f"Image file not found: {image_path}")
            return {
                'status': 'error',
                'image_path': str(image_path),
                'error': f'File not found: {image_path}'
            }
        except Exception as e:
            logger.error(f"Failed to analyze {image_path}: {e}", exc_info=True)
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
        """Analyze multiple images efficiently.

        Args:
            image_paths: List of image file paths
            progress_callback: Optional callback(current, total)

        Returns:
            List of result dicts
        """
        if not self.enabled:
            return [{
                'status': 'disabled',
                'image_path': str(path),
                'error': 'Content analysis is disabled'
            } for path in image_paths]

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

        if total > 0:
            avg_time = sum(r.get('processing_time_ms', 0) for r in results if r['status'] == 'success') / max(successful, 1)
            logger.info(
                f"Batch analysis complete: {successful} success, {failed} failed, "
                f"avg {avg_time:.0f}ms/image"
            )

        return results

    def get_category_suggestion(self, analysis_result: Dict) -> str:
        """Suggest a category based on analysis results.

        Args:
            analysis_result: Result from analyze_image()

        Returns:
            Suggested category name (e.g., 'Anime/Characters', 'Photos/People')
        """
        if analysis_result.get('status') != 'success':
            return 'Uncategorized'

        style = analysis_result.get('style', '')
        confidence = analysis_result.get('style_confidence', 0)
        persons_count = analysis_result.get('persons_detected', 0)

        # Get threshold for this style
        threshold = self.style_thresholds.get(style, 0.6)

        # High-confidence anime with persons
        if 'anime' in style.lower() and confidence >= threshold:
            if persons_count > 0:
                return 'Anime/Characters'
            else:
                return 'Anime/Scenery'

        # High-confidence realistic photos
        elif 'realistic' in style.lower() or 'photograph' in style.lower():
            if confidence >= threshold:
                if persons_count > 0:
                    return 'Photos/People'
                else:
                    return 'Photos/Other'
            else:
                return 'Photos/Uncategorized'

        # 3D renders
        elif '3d' in style.lower() or 'render' in style.lower():
            if confidence >= threshold:
                return '3D/Renders'
            else:
                return '3D/Uncategorized'

        # Low confidence - uncertain
        else:
            return 'Uncategorized'

    def is_enabled(self) -> bool:
        """Check if content analysis is enabled.

        Returns:
            True if enabled, False otherwise
        """
        return self.enabled

    def get_style_labels(self) -> List[str]:
        """Get list of configured style labels.

        Returns:
            List of style label strings
        """
        return self.style_labels.copy()
