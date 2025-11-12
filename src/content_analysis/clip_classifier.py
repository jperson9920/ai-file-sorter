"""CLIP-based zero-shot image classifier for style detection."""

import torch
from PIL import Image
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("transformers not installed. CLIP classification unavailable.")


class CLIPClassifier:
    """Zero-shot image classification using OpenAI's CLIP model."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", cache_dir: str = None):
        """Initialize CLIP model for zero-shot classification.

        Args:
            model_name: HuggingFace model identifier (default: ViT-B/32, ~150MB)
            cache_dir: Directory to cache downloaded models

        Raises:
            ImportError: If transformers package not installed
            RuntimeError: If model fails to load
        """
        if not CLIP_AVAILABLE:
            raise ImportError(
                "transformers package required for CLIP. "
                "Install with: pip install transformers"
            )

        logger.info(f"Loading CLIP model: {model_name}")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        try:
            self.processor = CLIPProcessor.from_pretrained(
                model_name,
                cache_dir=cache_dir
            )

            self.model = CLIPModel.from_pretrained(
                model_name,
                cache_dir=cache_dir
            ).to(self.device)

            self.model.eval()  # Set to inference mode

            logger.info(f"CLIP model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise RuntimeError(f"CLIP model loading failed: {e}")

    def classify(self, image: Image.Image, labels: List[str]) -> Dict[str, float]:
        """Classify image against candidate labels using zero-shot learning.

        Args:
            image: PIL Image to classify
            labels: List of text labels to classify against (e.g., ["anime", "realistic"])

        Returns:
            Dict mapping each label to confidence score (0-1), scores sum to ~1.0
        """
        try:
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

                # Calculate probabilities using softmax
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0]

                # Build result dict
                scores = {
                    label: prob.item()
                    for label, prob in zip(labels, probs)
                }

                logger.debug(f"CLIP scores: {scores}")

                return scores

        except Exception as e:
            logger.error(f"CLIP classification failed: {e}")
            # Return uniform distribution as fallback
            return {label: 1.0 / len(labels) for label in labels}

    def classify_batch(
        self,
        images: List[Image.Image],
        labels: List[str]
    ) -> List[Dict[str, float]]:
        """Classify multiple images efficiently in batch mode.

        Args:
            images: List of PIL Images
            labels: List of text labels to classify against

        Returns:
            List of score dicts, one per image
        """
        try:
            with torch.no_grad():
                # Batch processing
                inputs = self.processor(
                    text=labels,
                    images=images,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)

                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)

                # Convert to list of dicts
                results = []
                for image_probs in probs:
                    scores = {
                        label: prob.item()
                        for label, prob in zip(labels, image_probs)
                    }
                    results.append(scores)

                logger.debug(f"Batch classified {len(images)} images")

                return results

        except Exception as e:
            logger.error(f"CLIP batch classification failed: {e}")
            # Return uniform distributions as fallback
            fallback = {label: 1.0 / len(labels) for label in labels}
            return [fallback.copy() for _ in images]

    def get_best_match(self, image: Image.Image, labels: List[str]) -> tuple:
        """Get the best matching label for an image.

        Args:
            image: PIL Image
            labels: List of candidate labels

        Returns:
            Tuple of (best_label, confidence_score)
        """
        scores = self.classify(image, labels)
        best_label = max(scores, key=scores.get)
        best_score = scores[best_label]

        return best_label, best_score
