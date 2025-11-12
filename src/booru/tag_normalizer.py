"""Tag normalizer to convert booru tags to human-readable format."""

import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TagNormalizer:
    """Normalize booru tags to human-readable format."""

    # Tags to always filter out (meta tags)
    FILTER_TAGS = {
        'translation_request', 'commentary', 'commentary_request',
        'bad_id', 'bad_link', 'md5_mismatch', 'annotated',
        'check_translation', 'partially_translated', 'translated',
        'tagme', 'artist_request', 'character_request', 'source_request'
    }

    # Rating tags to filter
    RATING_TAGS = {'safe', 'questionable', 'explicit', 'sensitive'}

    @staticmethod
    def normalize_general_tag(tag: str) -> str:
        """Convert booru format to readable: blue_eyes -> Blue Eyes.

        Args:
            tag: Booru format tag with underscores

        Returns:
            Human-readable tag with spaces and title case
        """
        # Replace underscores with spaces
        readable = tag.replace('_', ' ')
        # Capitalize each word
        return readable.title()

    @staticmethod
    def normalize_character_tag(tag: str) -> Dict[str, str]:
        """Parse character tag: hinata_hyuga_(naruto) -> name + series.

        Args:
            tag: Character tag in format character_name_(series)

        Returns:
            Dictionary with 'name' and 'series' keys
        """
        # Pattern: character_name_(series_name)
        match = re.match(r'(.+?)_?\((.+?)\)', tag)
        if match:
            name = match.group(1).replace('_', ' ').title()
            series = match.group(2).replace('_', ' ').title()
            return {'name': name, 'series': series}
        else:
            # No series in parentheses
            return {'name': tag.replace('_', ' ').title(), 'series': None}

    @staticmethod
    def filter_tags(tags: List[str]) -> List[str]:
        """Remove meta tags and unwanted tags.

        Args:
            tags: List of raw booru tags

        Returns:
            Filtered list of tags
        """
        filtered = []
        for tag in tags:
            # Skip empty tags
            if not tag or not tag.strip():
                continue

            # Skip filtered tags
            if tag in TagNormalizer.FILTER_TAGS:
                continue

            # Skip rating tags
            if tag in TagNormalizer.RATING_TAGS:
                continue

            # Skip very short tags (likely artifacts)
            if len(tag) < 3:
                continue

            # Skip numeric-only tags
            if tag.isdigit():
                continue

            # Skip tags that are mostly numbers (like years, but keep valid tags)
            if sum(c.isdigit() for c in tag) / len(tag) > 0.7:
                continue

            filtered.append(tag)

        return filtered

    @classmethod
    def normalize_post_tags(cls, tag_data: Dict) -> Dict:
        """Normalize all tags from a post.

        Args:
            tag_data: Dictionary containing tag categories:
                - general: List of general tags
                - characters: List of character tags
                - series: List of copyright/series tags
                - artists: List of artist tags
                - rating: Content rating

        Returns:
            Normalized tag dictionary with same structure
        """
        try:
            # Filter and normalize general tags
            general = [cls.normalize_general_tag(t)
                       for t in cls.filter_tags(tag_data.get('general', []))]

            # Normalize character tags
            characters = [cls.normalize_character_tag(t)
                          for t in tag_data.get('characters', [])]

            # Normalize series tags
            series = [s.replace('_', ' ').title()
                      for s in tag_data.get('series', [])]

            # Normalize artist tags
            artists = [a.replace('_', ' ').title()
                       for a in tag_data.get('artists', [])]

            return {
                'general': general,
                'characters': characters,
                'series': series,
                'artists': artists,
                'rating': tag_data.get('rating', 'unknown')
            }
        except Exception as e:
            logger.error(f"Error normalizing tags: {e}")
            return {
                'general': [],
                'characters': [],
                'series': [],
                'artists': [],
                'rating': 'unknown'
            }

    @staticmethod
    def tags_to_flat_list(normalized_tags: Dict, include_characters: bool = True,
                          include_series: bool = True, include_artists: bool = False) -> List[str]:
        """Convert normalized tags to flat list for XMP writing.

        Args:
            normalized_tags: Normalized tag dictionary from normalize_post_tags()
            include_characters: Include character names
            include_series: Include series names
            include_artists: Include artist names

        Returns:
            Flat list of tag strings
        """
        tags = []

        # Add general tags
        tags.extend(normalized_tags.get('general', []))

        # Add character names
        if include_characters:
            for char in normalized_tags.get('characters', []):
                if isinstance(char, dict):
                    tags.append(char['name'])
                else:
                    tags.append(str(char))

        # Add series
        if include_series:
            tags.extend(normalized_tags.get('series', []))

        # Add artists
        if include_artists:
            tags.extend(normalized_tags.get('artists', []))

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag and tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags
