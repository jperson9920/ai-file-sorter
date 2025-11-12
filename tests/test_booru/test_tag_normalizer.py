"""Unit tests for tag normalizer."""

import pytest
from src.booru.tag_normalizer import TagNormalizer


class TestTagNormalizer:
    """Test cases for TagNormalizer class."""

    def test_normalize_general_tag(self):
        """Test general tag normalization."""
        assert TagNormalizer.normalize_general_tag("blue_eyes") == "Blue Eyes"
        assert TagNormalizer.normalize_general_tag("long_hair") == "Long Hair"
        assert TagNormalizer.normalize_general_tag("school_uniform") == "School Uniform"
        assert TagNormalizer.normalize_general_tag("one_word") == "One Word"

    def test_normalize_character_tag_with_series(self):
        """Test character tag normalization with series."""
        result = TagNormalizer.normalize_character_tag("hinata_hyuga_(naruto)")
        assert result['name'] == "Hinata Hyuga"
        assert result['series'] == "Naruto"

        result = TagNormalizer.normalize_character_tag("sailor_moon_(sailor_moon)")
        assert result['name'] == "Sailor Moon"
        assert result['series'] == "Sailor Moon"

    def test_normalize_character_tag_without_series(self):
        """Test character tag normalization without series."""
        result = TagNormalizer.normalize_character_tag("original_character")
        assert result['name'] == "Original Character"
        assert result['series'] is None

    def test_filter_tags_removes_meta_tags(self):
        """Test that meta tags are filtered out."""
        tags = ["blue_eyes", "translation_request", "long_hair", "commentary"]
        filtered = TagNormalizer.filter_tags(tags)

        assert "blue_eyes" in filtered
        assert "long_hair" in filtered
        assert "translation_request" not in filtered
        assert "commentary" not in filtered

    def test_filter_tags_removes_short_tags(self):
        """Test that very short tags are filtered out."""
        tags = ["blue_eyes", "ab", "x", "long_hair"]
        filtered = TagNormalizer.filter_tags(tags)

        assert "blue_eyes" in filtered
        assert "long_hair" in filtered
        assert "ab" not in filtered
        assert "x" not in filtered

    def test_filter_tags_removes_numeric_tags(self):
        """Test that numeric-only tags are filtered out."""
        tags = ["blue_eyes", "123", "456", "long_hair"]
        filtered = TagNormalizer.filter_tags(tags)

        assert "blue_eyes" in filtered
        assert "long_hair" in filtered
        assert "123" not in filtered
        assert "456" not in filtered

    def test_filter_tags_removes_rating_tags(self):
        """Test that rating tags are filtered out."""
        tags = ["blue_eyes", "safe", "questionable", "explicit", "long_hair"]
        filtered = TagNormalizer.filter_tags(tags)

        assert "blue_eyes" in filtered
        assert "long_hair" in filtered
        assert "safe" not in filtered
        assert "questionable" not in filtered
        assert "explicit" not in filtered

    def test_normalize_post_tags_full(self):
        """Test full post tag normalization."""
        tag_data = {
            'general': ['blue_eyes', 'long_hair', 'translation_request', 'school_uniform'],
            'characters': ['hinata_hyuga_(naruto)', 'sakura_haruno_(naruto)'],
            'series': ['naruto', 'naruto_shippuuden'],
            'artists': ['artist_name'],
            'rating': 'safe'
        }

        normalized = TagNormalizer.normalize_post_tags(tag_data)

        # Check general tags (filtered and normalized)
        assert "Blue Eyes" in normalized['general']
        assert "Long Hair" in normalized['general']
        assert "School Uniform" in normalized['general']
        # translation_request should be filtered out
        assert not any('Translation' in tag for tag in normalized['general'])

        # Check character tags
        assert len(normalized['characters']) == 2
        assert normalized['characters'][0]['name'] == "Hinata Hyuga"
        assert normalized['characters'][0]['series'] == "Naruto"

        # Check series tags
        assert "Naruto" in normalized['series']
        assert "Naruto Shippuuden" in normalized['series']

        # Check artists
        assert "Artist Name" in normalized['artists']

        # Check rating
        assert normalized['rating'] == 'safe'

    def test_normalize_post_tags_empty(self):
        """Test normalization with empty tag data."""
        tag_data = {}
        normalized = TagNormalizer.normalize_post_tags(tag_data)

        assert normalized['general'] == []
        assert normalized['characters'] == []
        assert normalized['series'] == []
        assert normalized['artists'] == []
        assert normalized['rating'] == 'unknown'

    def test_tags_to_flat_list(self):
        """Test converting normalized tags to flat list."""
        normalized_tags = {
            'general': ['Blue Eyes', 'Long Hair'],
            'characters': [
                {'name': 'Hinata Hyuga', 'series': 'Naruto'},
                {'name': 'Sakura Haruno', 'series': 'Naruto'}
            ],
            'series': ['Naruto'],
            'artists': ['Artist Name'],
            'rating': 'safe'
        }

        flat_tags = TagNormalizer.tags_to_flat_list(
            normalized_tags,
            include_characters=True,
            include_series=True,
            include_artists=False
        )

        assert 'Blue Eyes' in flat_tags
        assert 'Long Hair' in flat_tags
        assert 'Hinata Hyuga' in flat_tags
        assert 'Sakura Haruno' in flat_tags
        assert 'Naruto' in flat_tags
        assert 'Artist Name' not in flat_tags

    def test_tags_to_flat_list_no_duplicates(self):
        """Test that flat list removes duplicates."""
        normalized_tags = {
            'general': ['Blue Eyes', 'Blue Eyes', 'Long Hair'],
            'characters': [{'name': 'Character', 'series': 'Series'}],
            'series': ['Series'],  # This will be duplicate of character's series
            'artists': [],
            'rating': 'safe'
        }

        flat_tags = TagNormalizer.tags_to_flat_list(
            normalized_tags,
            include_characters=True,
            include_series=True,
            include_artists=False
        )

        # Should have Blue Eyes, Long Hair, Character, Series (no duplicates)
        assert len(flat_tags) == 4
        assert flat_tags.count('Blue Eyes') == 1
        assert flat_tags.count('Series') == 1

    def test_tags_to_flat_list_with_options(self):
        """Test flat list with different include options."""
        normalized_tags = {
            'general': ['Tag1', 'Tag2'],
            'characters': [{'name': 'Character', 'series': 'Series'}],
            'series': ['Series'],
            'artists': ['Artist'],
            'rating': 'safe'
        }

        # Only general tags
        flat_tags = TagNormalizer.tags_to_flat_list(
            normalized_tags,
            include_characters=False,
            include_series=False,
            include_artists=False
        )
        assert flat_tags == ['Tag1', 'Tag2']

        # Include everything
        flat_tags = TagNormalizer.tags_to_flat_list(
            normalized_tags,
            include_characters=True,
            include_series=True,
            include_artists=True
        )
        assert 'Tag1' in flat_tags
        assert 'Character' in flat_tags
        assert 'Series' in flat_tags
        assert 'Artist' in flat_tags
