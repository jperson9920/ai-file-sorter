"""SauceNAO client for reverse image search."""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Dict
import logging

try:
    from saucenao_api import AIOSauceNao
    from saucenao_api.errors import SauceNaoException
except ImportError:
    AIOSauceNao = None
    SauceNaoException = Exception

from .cache_manager import CacheManager
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SauceNAOClient:
    """Client for SauceNAO reverse image search with rate limiting and caching."""

    def __init__(self, api_key: Optional[str], cache_manager: CacheManager,
                 rate_limit: int = 6, min_similarity: float = 70.0):
        """Initialize SauceNAO client.

        Args:
            api_key: SauceNAO API key (optional, but recommended)
            cache_manager: Cache manager for storing results
            rate_limit: Maximum requests per 30 seconds (default: 6)
            min_similarity: Minimum similarity threshold (0-100)
        """
        if AIOSauceNao is None:
            raise ImportError("saucenao-api not installed. Install with: pip install saucenao-api")

        self.api_key = api_key
        self.sauce = AIOSauceNao(api_key=api_key) if api_key else AIOSauceNao()
        self.cache = cache_manager
        self.rate_limiter = RateLimiter(requests_per_30s=rate_limit)
        self.min_similarity = min_similarity

        if api_key:
            logger.info(f"SauceNAO client initialized with API key (rate limit: {rate_limit} req/30s)")
        else:
            logger.warning("SauceNAO client initialized without API key (limited to 100 searches/day)")

    def _hash_image(self, image_path: Path) -> str:
        """Generate SHA256 hash of image file.

        Args:
            image_path: Path to image file

        Returns:
            Hexadecimal SHA256 hash string
        """
        sha256 = hashlib.sha256()
        try:
            with open(image_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash image {image_path}: {e}")
            raise

    async def search_image(self, image_path: Path, min_similarity: Optional[float] = None) -> Dict:
        """Search for image and return best match.

        Args:
            image_path: Path to image file
            min_similarity: Override minimum similarity threshold

        Returns:
            Dictionary with search results:
                - status: 'success', 'no_match', or 'error'
                - similarity: Match similarity percentage (0-100)
                - url: Source URL of matched image
                - site: Name of the site where match was found
                - thumbnail: Thumbnail URL
                - error: Error message (if status is 'error')
        """
        if min_similarity is None:
            min_similarity = self.min_similarity

        # Check cache first
        try:
            image_hash = self._hash_image(image_path)
            cached = self.cache.get(image_hash)
            if cached:
                logger.debug(f"Cache hit for {image_path.name}")
                return cached
        except Exception as e:
            logger.warning(f"Cache check failed for {image_path}: {e}")
            image_hash = None

        # Rate limiting
        await self.rate_limiter.acquire()

        try:
            logger.info(f"Searching SauceNAO for: {image_path.name}")
            results = await self.sauce.from_file(str(image_path))

            if not results or len(results) == 0:
                result = {
                    'status': 'no_match',
                    'similarity': 0,
                    'url': None,
                    'site': None,
                    'thumbnail': None
                }
                logger.info(f"No match found for {image_path.name}")
            else:
                best_match = results[0]

                if best_match.similarity < min_similarity:
                    result = {
                        'status': 'no_match',
                        'similarity': best_match.similarity,
                        'url': None,
                        'site': None,
                        'thumbnail': None
                    }
                    logger.info(f"Match below threshold for {image_path.name}: "
                                f"{best_match.similarity:.1f}% < {min_similarity}%")
                else:
                    result = {
                        'status': 'success',
                        'similarity': best_match.similarity,
                        'url': best_match.urls[0] if best_match.urls else None,
                        'site': best_match.index_name,
                        'thumbnail': best_match.thumbnail
                    }
                    logger.info(f"Match found for {image_path.name}: "
                                f"{best_match.similarity:.1f}% on {best_match.index_name}")

            # Cache result
            if image_hash:
                try:
                    self.cache.set(image_hash, result)
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")

            return result

        except SauceNaoException as e:
            error_msg = str(e)
            logger.error(f"SauceNAO API error for {image_path.name}: {error_msg}")

            result = {
                'status': 'error',
                'error': error_msg,
                'similarity': 0,
                'url': None,
                'site': None,
                'thumbnail': None
            }

            # Don't cache errors
            return result

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Search failed for {image_path.name}: {error_msg}", exc_info=True)

            result = {
                'status': 'error',
                'error': error_msg,
                'similarity': 0,
                'url': None,
                'site': None,
                'thumbnail': None
            }

            return result

    async def search_batch(self, image_paths: list, min_similarity: Optional[float] = None) -> Dict[Path, Dict]:
        """Search multiple images with rate limiting.

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
                    'similarity': 0
                }

        return results

    async def close(self):
        """Close the SauceNAO client and cleanup resources."""
        if hasattr(self.sauce, 'close'):
            await self.sauce.close()
        logger.info("SauceNAO client closed")
