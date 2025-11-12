"""Unit tests for metadata builder."""

import pytest
from pathlib import Path
from src.xmp_writer.metadata_builder import MetadataBuilder


class TestMetadataBuilder:
    """Test cases for MetadataBuilder class."""

    def test_build_from_booru_tags_full(self):
        """Test building metadata from complete booru result."""
        booru_result = {
            'status': 'success',
            'similarity': 85.5,
            'source_site': 'Danbooru',
            'source_url': 'https://danbooru.donmai.us/posts/12345',
            'tags': {
                'general': ['blue eyes', 'long hair'],
                'characters': [
                    {'name': 'Hinata Hyuga', 'series': 'Naruto'}
                ],
                'series': ['Naruto'],
                'artists': ['Artist Name'],
                'rating': 'safe'
            }
        }

        metadata = MetadataBuilder.build_from_booru_tags(
            Path('test.jpg'),
            booru_result,
            include_rating=True
        )

        assert metadata['image_path'] == Path('test.jpg')
        assert 'blue eyes' in metadata['tags']
        assert 'long hair' in metadata['tags']
        assert 'Naruto/Hinata Hyuga' in metadata['tags']
        assert 'Series/Naruto' in metadata['tags']
        assert 'Artist/Artist Name' in metadata['tags']
        assert metadata['rating'] == 5
        assert 'Danbooru' in metadata['description']
        assert '85.5%' in metadata['description']
        assert metadata['source_url'] == 'https://danbooru.donmai.us/posts/12345'

    def test_build_from_booru_tags_flat(self):
        """Test building metadata without hierarchical tags."""
        booru_result = {
            'status': 'success',
            'tags': {
                'general': ['blue eyes'],
                'characters': [{'name': 'Character', 'series': 'Series'}],
                'series': ['Series']
            }
        }

        metadata = MetadataBuilder.build_from_booru_tags(
            Path('test.jpg'),
            booru_result,
            hierarchical_tags=False
        )

        assert 'Character' in metadata['tags']
        assert 'Series' in metadata['tags']
        # Should not have hierarchical format
        assert 'Series/Character' not in metadata['tags']

    def test_build_from_booru_tags_rating_map(self):
        """Test rating conversion from booru to 1-5 scale."""
        test_cases = [
            ('safe', 5),
            ('general', 5),
            ('sensitive', 4),
            ('questionable', 3),
            ('explicit', 1)
        ]

        for booru_rating, expected_stars in test_cases:
            booru_result = {
                'status': 'success',
                'tags': {
                    'general': [],
                    'rating': booru_rating
                }
            }

            metadata = MetadataBuilder.build_from_booru_tags(
                Path('test.jpg'),
                booru_result,
                include_rating=True
            )

            assert metadata['rating'] == expected_stars

    def test_build_from_booru_tags_no_match(self):
        """Test building metadata when no match found."""
        booru_result = {
            'status': 'no_match',
            'similarity': 0
        }

        metadata = MetadataBuilder.build_from_booru_tags(
            Path('test.jpg'),
            booru_result
        )

        assert metadata['tags'] == []
        assert metadata['description'] is None
        assert metadata['source_url'] is None

    def test_build_from_content_analysis(self):
        """Test building metadata from AI content analysis."""
        content_result = {
            'style': 'anime style illustration',
            'style_confidence': 0.85,
            'objects': [
                {'class': 'person', 'confidence': 0.92},
                {'class': 'building', 'confidence': 0.78}
            ],
            'persons_detected': 2
        }

        metadata = MetadataBuilder.build_from_content_analysis(
            Path('test.jpg'),
            content_result,
            min_confidence=0.6
        )

        assert metadata['image_path'] == Path('test.jpg')
        assert 'Style/Anime Style Illustration' in metadata['tags']
        assert 'Contains/Person' in metadata['tags']
        assert 'Contains/Building' in metadata['tags']
        assert 'Persons/2' in metadata['tags']
        assert 'AI Analysis' in metadata['description']

    def test_build_from_content_analysis_low_confidence(self):
        """Test that low confidence tags are excluded."""
        content_result = {
            'style': 'realistic',
            'style_confidence': 0.4,  # Below threshold
            'objects': [
                {'class': 'object1', 'confidence': 0.5},  # Below threshold
                {'class': 'object2', 'confidence': 0.8}   # Above threshold
            ]
        }

        metadata = MetadataBuilder.build_from_content_analysis(
            Path('test.jpg'),
            content_result,
            min_confidence=0.6
        )

        # Low confidence style should be excluded
        assert not any('realistic' in tag.lower() for tag in metadata['tags'])
        # Low confidence object should be excluded
        assert 'Contains/Object1' not in metadata['tags']
        # High confidence object should be included
        assert 'Contains/Object2' in metadata['tags']

    def test_build_from_flat_tags(self):
        """Test building metadata from flat tag list."""
        tags = ['tag1', 'tag2', 'tag3']
        metadata = MetadataBuilder.build_from_flat_tags(
            Path('test.jpg'),
            tags,
            description='Test description',
            rating=4,
            source_url='https://example.com'
        )

        assert metadata['image_path'] == Path('test.jpg')
        assert metadata['tags'] == tags
        assert metadata['description'] == 'Test description'
        assert metadata['rating'] == 4
        assert metadata['source_url'] == 'https://example.com'

    def test_merge_metadata_two_dicts(self):
        """Test merging two metadata dicts."""
        meta1 = {
            'image_path': Path('test.jpg'),
            'tags': ['tag1', 'tag2'],
            'description': 'First description',
            'rating': None,
            'source_url': None
        }

        meta2 = {
            'image_path': Path('test.jpg'),
            'tags': ['tag2', 'tag3'],  # tag2 is duplicate
            'description': None,
            'rating': 5,
            'source_url': 'https://example.com'
        }

        merged = MetadataBuilder.merge_metadata(meta1, meta2)

        # Tags should be combined and deduplicated
        assert set(merged['tags']) == {'tag1', 'tag2', 'tag3'}
        # Should keep first description
        assert merged['description'] == 'First description'
        # Should use rating from second dict
        assert merged['rating'] == 5
        # Should use source_url from second dict
        assert merged['source_url'] == 'https://example.com'

    def test_merge_metadata_multiple_dicts(self):
        """Test merging more than two metadata dicts."""
        meta1 = {'image_path': Path('test.jpg'), 'tags': ['a', 'b']}
        meta2 = {'image_path': Path('test.jpg'), 'tags': ['c', 'd']}
        meta3 = {'image_path': Path('test.jpg'), 'tags': ['e', 'f']}

        merged = MetadataBuilder.merge_metadata(meta1, meta2, meta3)

        assert set(merged['tags']) == {'a', 'b', 'c', 'd', 'e', 'f'}

    def test_merge_metadata_preserves_order(self):
        """Test that tag order is preserved during merge."""
        meta1 = {'image_path': Path('test.jpg'), 'tags': ['tag1', 'tag2', 'tag3']}
        meta2 = {'image_path': Path('test.jpg'), 'tags': ['tag4', 'tag2']}  # tag2 duplicate

        merged = MetadataBuilder.merge_metadata(meta1, meta2)

        # tag2 should appear only once in its first position
        tags = merged['tags']
        assert tags.index('tag1') < tags.index('tag2')
        assert tags.index('tag2') < tags.index('tag3')
        assert tags.index('tag3') < tags.index('tag4')

    def test_filter_tags_max_tags(self):
        """Test limiting number of tags."""
        tags = ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']
        filtered = MetadataBuilder.filter_tags(tags, max_tags=3)

        assert len(filtered) == 3
        assert filtered == ['tag1', 'tag2', 'tag3']

    def test_filter_tags_exclude_prefixes(self):
        """Test excluding tags by prefix."""
        tags = ['blue eyes', 'Artist/John', 'long hair', 'Artist/Jane', 'Series/Naruto']
        filtered = MetadataBuilder.filter_tags(
            tags,
            exclude_prefixes=['Artist/']
        )

        assert 'blue eyes' in filtered
        assert 'long hair' in filtered
        assert 'Series/Naruto' in filtered
        assert 'Artist/John' not in filtered
        assert 'Artist/Jane' not in filtered

    def test_filter_tags_combined(self):
        """Test filtering with both max_tags and exclude_prefixes."""
        tags = ['tag1', 'Artist/A', 'tag2', 'Artist/B', 'tag3', 'tag4']
        filtered = MetadataBuilder.filter_tags(
            tags,
            max_tags=3,
            exclude_prefixes=['Artist/']
        )

        # Should exclude Artist/ tags, then limit to 3
        assert len(filtered) == 3
        assert filtered == ['tag1', 'tag2', 'tag3']
        assert 'Artist/A' not in filtered
        assert 'Artist/B' not in filtered

    def test_validate_metadata_valid(self):
        """Test validation of valid metadata."""
        metadata = {
            'image_path': Path('test.jpg'),
            'tags': ['tag1', 'tag2'],
            'description': 'Test',
            'rating': 3,
            'source_url': 'https://example.com'
        }

        assert MetadataBuilder.validate_metadata(metadata) is True

    def test_validate_metadata_missing_required(self):
        """Test validation fails for missing required fields."""
        # Missing image_path
        metadata1 = {'tags': ['tag1']}
        assert MetadataBuilder.validate_metadata(metadata1) is False

        # Missing tags
        metadata2 = {'image_path': Path('test.jpg')}
        assert MetadataBuilder.validate_metadata(metadata2) is False

    def test_validate_metadata_invalid_types(self):
        """Test validation fails for invalid field types."""
        # image_path not Path
        metadata1 = {'image_path': 'test.jpg', 'tags': []}
        assert MetadataBuilder.validate_metadata(metadata1) is False

        # tags not list
        metadata2 = {'image_path': Path('test.jpg'), 'tags': 'tag1,tag2'}
        assert MetadataBuilder.validate_metadata(metadata2) is False

    def test_validate_metadata_invalid_rating(self):
        """Test validation fails for invalid rating values."""
        # Rating too high
        metadata1 = {
            'image_path': Path('test.jpg'),
            'tags': [],
            'rating': 10
        }
        assert MetadataBuilder.validate_metadata(metadata1) is False

        # Rating negative
        metadata2 = {
            'image_path': Path('test.jpg'),
            'tags': [],
            'rating': -1
        }
        assert MetadataBuilder.validate_metadata(metadata2) is False

        # Rating not integer
        metadata3 = {
            'image_path': Path('test.jpg'),
            'tags': [],
            'rating': 3.5
        }
        assert MetadataBuilder.validate_metadata(metadata3) is False
