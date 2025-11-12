"""Metadata builder for constructing XMP metadata from various sources."""

from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MetadataBuilder:
    """Build metadata structures for XMP writing from different sources."""

    @staticmethod
    def build_from_booru_tags(
        image_path: Path,
        booru_result: Dict,
        include_rating: bool = False,
        hierarchical_tags: bool = True
    ) -> Dict:
        """Build metadata dict from booru search results.

        Args:
            image_path: Path to image file
            booru_result: Result from BooruSearcher.search_and_tag()
            include_rating: Whether to include rating in metadata
            hierarchical_tags: Use hierarchical format (Series/Character)

        Returns:
            Dict suitable for ExifToolWrapper.write_xmp_sidecar()
        """
        metadata = {
            'image_path': image_path,
            'tags': [],
            'description': None,
            'rating': None,
            'source_url': None
        }

        # Extract tags from booru result
        if 'tags' in booru_result and booru_result['tags']:
            tags_data = booru_result['tags']
            all_tags = []

            # General tags (descriptive)
            general_tags = tags_data.get('general', [])
            all_tags.extend(general_tags)

            # Character tags
            characters = tags_data.get('characters', [])
            for char in characters:
                if isinstance(char, dict):
                    name = char.get('name', '')
                    series = char.get('series', '')

                    if hierarchical_tags and series:
                        # Hierarchical: Naruto/Hinata Hyuga
                        char_tag = f"{series}/{name}"
                    else:
                        # Flat: Hinata Hyuga
                        char_tag = name

                    if char_tag:
                        all_tags.append(char_tag)
                elif char:
                    all_tags.append(str(char))

            # Series tags
            series_list = tags_data.get('series', [])
            if hierarchical_tags:
                all_tags.extend([f"Series/{s}" for s in series_list if s])
            else:
                all_tags.extend(series_list)

            # Artist tags (optional - usually not included in image tags)
            artists = tags_data.get('artists', [])
            if artists and hierarchical_tags:
                all_tags.extend([f"Artist/{a}" for a in artists if a])

            metadata['tags'] = all_tags

        # Description from similarity and source
        if booru_result.get('status') == 'success':
            similarity = booru_result.get('similarity', 0)
            source = booru_result.get('source_site', 'unknown')
            if similarity and source:
                metadata['description'] = f"Matched via {source} ({similarity:.1f}% similarity)"

        # Source URL
        if booru_result.get('source_url'):
            metadata['source_url'] = booru_result['source_url']

        # Rating (convert booru rating to 1-5 star scale)
        if include_rating and 'tags' in booru_result:
            rating_value = booru_result['tags'].get('rating', '')
            rating_map = {
                'safe': 5,
                'general': 5,
                'sensitive': 4,
                'questionable': 3,
                'explicit': 1
            }
            if rating_value in rating_map:
                metadata['rating'] = rating_map[rating_value]

        logger.debug(f"Built metadata for {image_path.name}: {len(metadata['tags'])} tags")

        return metadata

    @staticmethod
    def build_from_content_analysis(
        image_path: Path,
        content_result: Dict,
        min_confidence: float = 0.6
    ) -> Dict:
        """Build metadata dict from AI content analysis results.

        Args:
            image_path: Path to image file
            content_result: Result from ContentAnalyzer
            min_confidence: Minimum confidence threshold for tags

        Returns:
            Dict suitable for ExifToolWrapper.write_xmp_sidecar()
        """
        metadata = {
            'image_path': image_path,
            'tags': [],
            'description': None,
            'rating': None,
            'source_url': None
        }

        tags = []

        # Add style classification tags
        if 'style' in content_result:
            style = content_result['style']
            confidence = content_result.get('style_confidence', 0)

            if confidence >= min_confidence:
                # Add hierarchical style tag
                tags.append(f"Style/{style.title()}")

                # Log low confidence
                if confidence < 0.8:
                    logger.debug(f"Low confidence style tag for {image_path.name}: "
                                 f"{style} ({confidence:.2f})")

        # Add object detection tags
        if 'objects' in content_result:
            for obj in content_result['objects']:
                obj_class = obj.get('class', '')
                confidence = obj.get('confidence', 0)

                if confidence >= min_confidence and obj_class:
                    # Add hierarchical object tag
                    tags.append(f"Contains/{obj_class.title()}")

        # Add detected persons count
        if 'persons_detected' in content_result:
            person_count = content_result['persons_detected']
            if person_count > 0:
                tags.append(f"Persons/{person_count}")

        metadata['tags'] = tags

        # Description
        components = []
        if 'style' in content_result:
            components.append(f"Style: {content_result['style']}")
        if 'objects' in content_result and content_result['objects']:
            obj_names = [o['class'] for o in content_result['objects'][:3]]
            components.append(f"Objects: {', '.join(obj_names)}")

        if components:
            metadata['description'] = "AI Analysis - " + "; ".join(components)
        else:
            metadata['description'] = "Analyzed by AI content classifier"

        logger.debug(f"Built AI metadata for {image_path.name}: {len(tags)} tags")

        return metadata

    @staticmethod
    def build_from_flat_tags(
        image_path: Path,
        tags: List[str],
        description: Optional[str] = None,
        rating: Optional[int] = None,
        source_url: Optional[str] = None
    ) -> Dict:
        """Build metadata dict from flat tag list.

        Args:
            image_path: Path to image file
            tags: List of tag strings
            description: Optional description
            rating: Optional rating (0-5)
            source_url: Optional source URL

        Returns:
            Dict suitable for ExifToolWrapper.write_xmp_sidecar()
        """
        return {
            'image_path': image_path,
            'tags': tags,
            'description': description,
            'rating': rating,
            'source_url': source_url
        }

    @staticmethod
    def merge_metadata(
        *metadata_dicts: Dict
    ) -> Dict:
        """Merge multiple metadata dicts, combining tags and preferring non-None values.

        Args:
            *metadata_dicts: Variable number of metadata dicts to merge

        Returns:
            Merged metadata dict
        """
        if not metadata_dicts:
            return {
                'image_path': None,
                'tags': [],
                'description': None,
                'rating': None,
                'source_url': None
            }

        # Start with first dict
        merged = metadata_dicts[0].copy()

        # Merge remaining dicts
        for additional in metadata_dicts[1:]:
            # Combine tags (deduplicate while preserving order)
            existing_tags = merged.get('tags', [])
            new_tags = additional.get('tags', [])

            # Use dict to track seen tags (preserves order in Python 3.7+)
            all_tags_dict = {tag: None for tag in existing_tags}
            all_tags_dict.update({tag: None for tag in new_tags})
            merged['tags'] = list(all_tags_dict.keys())

            # Prefer non-None values for other fields
            for key in ['description', 'rating', 'source_url']:
                if not merged.get(key) and additional.get(key):
                    merged[key] = additional[key]

            # Always use the image_path from the most recent metadata
            if additional.get('image_path'):
                merged['image_path'] = additional['image_path']

        logger.debug(f"Merged {len(metadata_dicts)} metadata dicts: "
                     f"{len(merged['tags'])} total tags")

        return merged

    @staticmethod
    def filter_tags(
        tags: List[str],
        max_tags: Optional[int] = None,
        exclude_prefixes: Optional[List[str]] = None
    ) -> List[str]:
        """Filter and limit tags.

        Args:
            tags: List of tags
            max_tags: Maximum number of tags to keep (None = no limit)
            exclude_prefixes: List of prefixes to exclude (e.g., ['Artist/'])

        Returns:
            Filtered list of tags
        """
        filtered = tags.copy()

        # Exclude by prefix
        if exclude_prefixes:
            filtered = [
                tag for tag in filtered
                if not any(tag.startswith(prefix) for prefix in exclude_prefixes)
            ]

        # Limit count
        if max_tags and len(filtered) > max_tags:
            filtered = filtered[:max_tags]
            logger.debug(f"Limited tags from {len(tags)} to {max_tags}")

        return filtered

    @staticmethod
    def validate_metadata(metadata: Dict) -> bool:
        """Validate metadata dict has required fields.

        Args:
            metadata: Metadata dict to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['image_path', 'tags']

        for field in required_fields:
            if field not in metadata:
                logger.error(f"Metadata missing required field: {field}")
                return False

        # Validate image_path
        if not isinstance(metadata['image_path'], Path):
            logger.error(f"image_path must be Path object, got {type(metadata['image_path'])}")
            return False

        # Validate tags is a list
        if not isinstance(metadata['tags'], list):
            logger.error(f"tags must be list, got {type(metadata['tags'])}")
            return False

        # Validate rating if present
        if metadata.get('rating') is not None:
            rating = metadata['rating']
            if not isinstance(rating, int) or rating < 0 or rating > 5:
                logger.error(f"rating must be integer 0-5, got {rating}")
                return False

        return True
