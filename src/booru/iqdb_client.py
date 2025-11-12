"""IQDB client for reverse image search as fallback."""

from pathlib import Path
from typing import Optional, Dict
import logging

try:
    from PicImageSearch import Iqdb
except ImportError:
    Iqdb = None

logger = logging.getLogger(__name__)


class IQDBClient:
    """Fallback search client using IQDB."""

    def __init__(self, min_similarity: float = 80.0):
        """Initialize IQDB client.

        Args:
            min_similarity: Minimum similarity threshold (0-100)
        """
        if Iqdb is None:
            raise ImportError("PicImageSearch not installed. Install with: pip install PicImageSearch")

        self.client = Iqdb()
        self.min_similarity = min_similarity
        logger.info(f"IQDB client initialized (min similarity: {min_similarity}%)")

    async def search_image(self, image_path: Path, min_similarity: Optional[float] = None) -> Dict:
        """Search IQDB for similar images.

        Args:
            image_path: Path to image file
            min_similarity: Override minimum similarity threshold

        Returns:
            Dictionary with search results (same format as SauceNAO):
                - status: 'success', 'no_match', or 'error'
                - similarity: Match similarity percentage
                - url: Source URL of matched image
                - site: 'IQDB'
                - thumbnail: Thumbnail URL
                - error: Error message (if status is 'error')
        """
        if min_similarity is None:
            min_similarity = self.min_similarity

        try:
            logger.info(f"Searching IQDB for: {image_path.name}")
            result = await self.client.search(file=str(image_path))

            if not result or not result.raw or len(result.raw) == 0:
                logger.info(f"No match found on IQDB for {image_path.name}")
                return {
                    'status': 'no_match',
                    'similarity': 0,
                    'url': None,
                    'site': 'IQDB',
                    'thumbnail': None
                }

            # Get best match
            best_match = result.raw[0]

            # Extract similarity - may be string or float
            try:
                if hasattr(best_match, 'similarity'):
                    similarity = float(best_match.similarity)
                else:
                    # Try to extract from content
                    similarity = 0.0
            except (ValueError, TypeError, AttributeError):
                logger.warning(f"Could not parse similarity for {image_path.name}")
                similarity = 0.0

            if similarity < min_similarity:
                logger.info(f"Match below threshold for {image_path.name}: "
                            f"{similarity:.1f}% < {min_similarity}%")
                return {
                    'status': 'no_match',
                    'similarity': similarity,
                    'url': None,
                    'site': 'IQDB',
                    'thumbnail': None
                }

            # Extract URL
            url = None
            if hasattr(best_match, 'url'):
                url = best_match.url
            elif hasattr(best_match, 'source'):
                url = best_match.source

            # Extract thumbnail
            thumbnail = None
            if hasattr(best_match, 'thumbnail'):
                thumbnail = best_match.thumbnail
            elif hasattr(best_match, 'thumb'):
                thumbnail = best_match.thumb

            logger.info(f"Match found on IQDB for {image_path.name}: {similarity:.1f}%")

            return {
                'status': 'success',
                'similarity': similarity,
                'url': url,
                'site': 'IQDB',
                'thumbnail': thumbnail
            }

        except Exception as e:
            error_msg = f"IQDB search error: {str(e)}"
            logger.error(f"Search failed for {image_path.name}: {error_msg}", exc_info=True)

            return {
                'status': 'error',
                'error': error_msg,
                'similarity': 0,
                'url': None,
                'site': 'IQDB',
                'thumbnail': None
            }

    async def search_batch(self, image_paths: list, min_similarity: Optional[float] = None) -> Dict[Path, Dict]:
        """Search multiple images.

        Args:
            image_paths: List of image file paths
            min_similarity: Override minimum similarity threshold

        Returns:
            Dictionary mapping image paths to search results
        """
        results = {}

        for image_path in image_paths:
            path = Path(image_path)
            try:
                result = await self.search_image(path, min_similarity)
                results[path] = result
            except Exception as e:
                logger.error(f"Failed to search {path}: {e}")
                results[path] = {
                    'status': 'error',
                    'error': str(e),
                    'similarity': 0,
                    'site': 'IQDB'
                }

        return results
