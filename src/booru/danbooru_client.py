"""Danbooru client for extracting tags from posts."""

from pybooru import Danbooru
from typing import Optional, List, Dict
import re
import logging

logger = logging.getLogger(__name__)


class DanbooruClient:
    """Client for interacting with Danbooru API to extract tags."""

    def __init__(self, username: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize Danbooru client.

        Args:
            username: Danbooru account username (optional for basic access)
            api_key: Danbooru API key (optional for basic access)
        """
        self.username = username
        self.api_key = api_key

        # Initialize client with or without authentication
        if username and api_key:
            self.client = Danbooru('danbooru', username=username, api_key=api_key)
            logger.info("Danbooru client initialized with authentication")
        else:
            self.client = Danbooru('danbooru')
            logger.info("Danbooru client initialized without authentication (limited access)")

    def extract_post_id(self, url: str) -> Optional[int]:
        """Extract post ID from Danbooru or booru-style URL.

        Args:
            url: URL from reverse search result

        Returns:
            Post ID as integer, or None if not found
        """
        if not url:
            return None

        # Patterns for different Danbooru URL formats
        patterns = [
            r'danbooru\.donmai\.us/posts/(\d+)',
            r'danbooru\.donmai\.us/post/show/(\d+)',
            r'/posts/(\d+)',
            r'id=(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                post_id = int(match.group(1))
                logger.debug(f"Extracted post ID {post_id} from URL: {url}")
                return post_id

        logger.warning(f"Could not extract post ID from URL: {url}")
        return None

    def get_tags(self, post_id: int, max_tags: int = 10) -> Dict[str, List[str]]:
        """Retrieve tags for a Danbooru post.

        Args:
            post_id: Danbooru post ID
            max_tags: Maximum number of general tags to return (most popular first)

        Returns:
            Dictionary with tag categories:
                - general: General descriptive tags
                - characters: Character tags
                - series: Copyright/series tags
                - artists: Artist tags
                - rating: Content rating (safe/questionable/explicit)
        """
        try:
            post = self.client.post_show(post_id)

            # Extract different tag categories
            # Danbooru separates tags by category automatically
            general_tags = post.get('tag_string_general', '').split()
            character_tags = post.get('tag_string_character', '').split()
            copyright_tags = post.get('tag_string_copyright', '').split()
            artist_tags = post.get('tag_string_artist', '').split()

            # Limit general tags to max_tags (they're already sorted by popularity on Danbooru)
            if len(general_tags) > max_tags:
                general_tags = general_tags[:max_tags]

            rating = post.get('rating', 'unknown')
            # Map Danbooru rating codes to full names
            rating_map = {
                's': 'safe',
                'q': 'questionable',
                'e': 'explicit',
                'g': 'general'  # Danbooru's new general rating
            }
            rating = rating_map.get(rating, rating)

            result = {
                'general': general_tags,
                'characters': character_tags,
                'series': copyright_tags,
                'artists': artist_tags,
                'rating': rating
            }

            logger.info(f"Retrieved tags for post {post_id}: "
                        f"{len(general_tags)} general, "
                        f"{len(character_tags)} characters, "
                        f"{len(copyright_tags)} series")

            return result

        except Exception as e:
            logger.error(f"Failed to fetch tags for post {post_id}: {e}")
            raise Exception(f"Failed to fetch tags for post {post_id}: {e}")

    def get_tags_from_url(self, url: str, max_tags: int = 10) -> Optional[Dict[str, List[str]]]:
        """Extract post ID from URL and retrieve tags.

        Args:
            url: Danbooru post URL
            max_tags: Maximum number of general tags to return

        Returns:
            Tag dictionary or None if post ID couldn't be extracted
        """
        post_id = self.extract_post_id(url)
        if post_id is None:
            return None

        try:
            return self.get_tags(post_id, max_tags)
        except Exception as e:
            logger.error(f"Error getting tags from URL {url}: {e}")
            return None

    def is_authenticated(self) -> bool:
        """Check if client is authenticated.

        Returns:
            True if username and API key are provided
        """
        return bool(self.username and self.api_key)
