"""Unified booru search interface combining SauceNAO, IQDB, and Danbooru."""

from pathlib import Path
from typing import Optional, Dict, List
import logging

from .saucenao_client import SauceNAOClient
from .iqdb_client import IQDBClient
from .danbooru_client import DanbooruClient
from .tag_normalizer import TagNormalizer
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class BooruSearcher:
    """Unified interface for reverse image search and tag extraction."""

    def __init__(self, config: Dict):
        """Initialize booru searcher with configuration.

        Args:
            config: Configuration dictionary with API keys and settings
        """
        self.config = config

        # Initialize cache manager
        cache_config = config.get('performance', {})
        cache_path = config.get('learning', {}).get('database_path', 'data/preferences.db')
        cache_path = str(Path(cache_path).parent / 'search_cache.db')
        cache_ttl = cache_config.get('cache_ttl_hours', 48)

        self.cache_manager = CacheManager(cache_path, cache_ttl)

        # Initialize SauceNAO client
        saucenao_config = config.get('api', {}).get('saucenao', {})
        self.saucenao = SauceNAOClient(
            api_key=saucenao_config.get('api_key'),
            cache_manager=self.cache_manager,
            rate_limit=saucenao_config.get('rate_limit', 6),
            min_similarity=saucenao_config.get('min_similarity', 70.0)
        )

        # Initialize IQDB client (fallback)
        iqdb_config = config.get('api', {}).get('iqdb', {})
        self.iqdb_enabled = iqdb_config.get('enabled', True)
        if self.iqdb_enabled:
            self.iqdb = IQDBClient(
                min_similarity=iqdb_config.get('min_similarity', 80.0)
            )
        else:
            self.iqdb = None

        # Initialize Danbooru client
        danbooru_config = config.get('api', {}).get('danbooru', {})
        self.danbooru = DanbooruClient(
            username=danbooru_config.get('username'),
            api_key=danbooru_config.get('api_key')
        )

        # Tag normalizer
        self.tag_normalizer = TagNormalizer()

        logger.info("BooruSearcher initialized successfully")

    async def search_and_tag(self, image_path: Path, max_tags: int = 10) -> Dict:
        """Perform reverse search and extract tags.

        Args:
            image_path: Path to image file
            max_tags: Maximum number of general tags to return

        Returns:
            Dictionary with complete results:
                - status: 'success', 'no_match', or 'error'
                - similarity: Match similarity percentage
                - source_url: URL of matched post
                - source_site: Site where match was found
                - tags: Normalized tag dictionary
                - raw_tags: Raw tag dictionary from Danbooru
                - flat_tags: Flat list of tags for XMP
        """
        result = {
            'status': 'no_match',
            'similarity': 0,
            'source_url': None,
            'source_site': None,
            'tags': None,
            'raw_tags': None,
            'flat_tags': []
        }

        try:
            # Try SauceNAO first
            search_result = await self.saucenao.search_image(image_path)

            # Fallback to IQDB if SauceNAO fails or finds no match
            if self.iqdb and (search_result['status'] == 'no_match' or search_result['status'] == 'error'):
                logger.info(f"Falling back to IQDB for {image_path.name}")
                search_result = await self.iqdb.search_image(image_path)

            # Update result with search info
            result['status'] = search_result['status']
            result['similarity'] = search_result.get('similarity', 0)
            result['source_url'] = search_result.get('url')
            result['source_site'] = search_result.get('site')

            # If we found a match, try to extract tags
            if search_result['status'] == 'success' and search_result.get('url'):
                try:
                    # Extract tags from Danbooru
                    tags = self.danbooru.get_tags_from_url(search_result['url'], max_tags)

                    if tags:
                        # Normalize tags
                        normalized_tags = self.tag_normalizer.normalize_post_tags(tags)

                        # Create flat tag list for XMP
                        flat_tags = self.tag_normalizer.tags_to_flat_list(
                            normalized_tags,
                            include_characters=True,
                            include_series=True,
                            include_artists=False  # Usually don't include artists in image tags
                        )

                        result['raw_tags'] = tags
                        result['tags'] = normalized_tags
                        result['flat_tags'] = flat_tags

                        logger.info(f"Successfully extracted {len(flat_tags)} tags for {image_path.name}")
                    else:
                        logger.warning(f"No tags found for {image_path.name} at {search_result['url']}")

                except Exception as e:
                    logger.error(f"Failed to extract tags for {image_path.name}: {e}")
                    # Keep the search result even if tag extraction fails
                    result['status'] = 'success_no_tags'

            return result

        except Exception as e:
            logger.error(f"Search failed for {image_path.name}: {e}", exc_info=True)
            result['status'] = 'error'
            result['error'] = str(e)
            return result

    async def search_batch(self, image_paths: List[Path], max_tags: int = 10) -> Dict[Path, Dict]:
        """Search and tag multiple images.

        Args:
            image_paths: List of image file paths
            max_tags: Maximum number of general tags per image

        Returns:
            Dictionary mapping image paths to results
        """
        results = {}

        for image_path in image_paths:
            try:
                result = await self.search_and_tag(image_path, max_tags)
                results[image_path] = result
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                results[image_path] = {
                    'status': 'error',
                    'error': str(e),
                    'similarity': 0
                }

        return results

    def get_cache_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return self.cache_manager.get_stats()

    def cleanup_cache(self) -> int:
        """Clean up expired cache entries.

        Returns:
            Number of entries deleted
        """
        return self.cache_manager.cleanup_expired()

    async def close(self):
        """Close all clients and cleanup resources."""
        await self.saucenao.close()
        logger.info("BooruSearcher closed")
