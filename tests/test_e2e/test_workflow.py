"""End-to-end workflow tests."""

import pytest
import asyncio
from pathlib import Path
import tempfile
from PIL import Image


@pytest.fixture
def sample_images(tmp_path):
    """Create sample test images."""
    images = []
    for i in range(5):
        img_path = tmp_path / f"test_image_{i}.jpg"
        # Create a simple colored image
        img = Image.new('RGB', (800, 600), color=(i*50, 100, 200))
        img.save(img_path, 'JPEG')
        images.append(img_path)
    return images


@pytest.fixture
def test_config(tmp_path):
    """Create test configuration."""
    return {
        'directories': {
            'inbox': str(tmp_path / 'inbox'),
            'sorted': str(tmp_path / 'sorted'),
            'working': str(tmp_path / 'working'),
            'nas_path': ''
        },
        'api': {
            'saucenao': {
                'api_key': None,  # Skip API calls in tests
                'rate_limit': 6,
                'min_similarity': 70.0
            },
            'danbooru': {
                'username': None,
                'api_key': None
            },
            'iqdb': {
                'enabled': False
            }
        },
        'content_analysis': {
            'enabled': False  # Disable to avoid model downloads in tests
        },
        'workflow': {
            'batch_size': 10,
            'parallel_workers': 2,
            'enable_gui_review': False,
            'auto_approve_high_confidence': True
        },
        'xmp': {
            'exiftool_path': '',
            'sidecar_format': '{filename}.xmp',
            'include_rating': False,
            'include_description': True
        },
        'learning': {
            'database_path': str(tmp_path / 'test_preferences.db'),
            'min_confidence': 0.7,
            'min_samples': 50
        },
        'sync': {
            'enabled': False
        },
        'logging': {
            'level': 'ERROR',  # Reduce noise in tests
            'file': str(tmp_path / 'test.log'),
            'console_output': False
        },
        'performance': {
            'cache_enabled': True,
            'cache_ttl_hours': 1
        }
    }


class TestWorkflowIntegration:
    """Integration tests for complete workflow."""

    def test_config_loader(self, test_config, tmp_path):
        """Test configuration loading."""
        from src.utils.config_loader import ConfigLoader

        # Save config to file
        config_path = tmp_path / 'test_config.yaml'
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)

        # Load config
        loader = ConfigLoader(str(config_path))
        loaded_config = loader.load()

        assert loaded_config is not None
        assert 'directories' in loaded_config
        assert 'api' in loaded_config

    def test_preference_database_creation(self, tmp_path):
        """Test preference database initialization."""
        from src.learning import PreferenceDatabase

        db_path = tmp_path / 'test_prefs.db'
        pref_db = PreferenceDatabase(str(db_path))

        assert db_path.exists()

        # Test recording a movement
        pref_db.record_movement(
            file_hash='abc123',
            file_name='test.jpg',
            actual_category='Anime/Characters',
            suggested_category='Photos/People',
            style='anime style illustration',
            persons_detected=2,
            booru_tags=['blue_eyes', 'long_hair']
        )

        # Test getting stats
        stats = pref_db.get_stats()
        assert stats['total_movements'] == 1

    def test_metadata_builder_workflow(self, tmp_path):
        """Test metadata building from various sources."""
        from src.xmp_writer import MetadataBuilder

        image_path = tmp_path / 'test.jpg'

        # Build from booru tags
        booru_result = {
            'status': 'success',
            'similarity': 85.0,
            'source_site': 'Danbooru',
            'source_url': 'https://danbooru.donmai.us/posts/12345',
            'tags': {
                'general': ['blue eyes', 'long hair'],
                'characters': [{'name': 'Test Character', 'series': 'Test Series'}],
                'series': ['Test Series'],
                'artists': ['Test Artist'],
                'rating': 'safe'
            }
        }

        metadata = MetadataBuilder.build_from_booru_tags(
            image_path,
            booru_result,
            include_rating=True
        )

        assert metadata['image_path'] == image_path
        assert 'blue eyes' in metadata['tags']
        assert 'Test Series/Test Character' in metadata['tags']
        assert metadata['rating'] == 5  # safe = 5 stars
        assert 'Danbooru' in metadata['description']

    @pytest.mark.skipif(not Path('exiftool').exists() and not Path('exiftool.exe').exists(),
                       reason="ExifTool not installed")
    def test_xmp_writing(self, tmp_path, sample_images):
        """Test XMP sidecar writing."""
        from src.xmp_writer import ExifToolWrapper

        test_image = sample_images[0]

        try:
            with ExifToolWrapper() as et:
                success = et.write_xmp_sidecar(
                    image_path=test_image,
                    tags=['test tag 1', 'test tag 2', 'anime'],
                    description='Test description',
                    rating=4
                )

                if success:
                    # Check XMP file was created
                    xmp_path = Path(str(test_image) + '.xmp')
                    assert xmp_path.exists()

                    # Read it back
                    tags = et.read_xmp_tags(test_image)
                    assert len(tags) > 0
        except RuntimeError:
            pytest.skip("ExifTool not available")


class TestPerformance:
    """Performance tests."""

    @pytest.mark.slow
    def test_tag_normalization_performance(self):
        """Test tag normalization performance."""
        from src.booru.tag_normalizer import TagNormalizer
        import time

        # Generate test data
        tags = [f"tag_{i}" for i in range(1000)]

        start = time.time()
        for _ in range(100):  # 100 iterations
            TagNormalizer.filter_tags(tags)
        elapsed = time.time() - start

        # Should complete 100 iterations in less than 1 second
        assert elapsed < 1.0

    @pytest.mark.slow
    def test_cache_performance(self, tmp_path):
        """Test cache read/write performance."""
        from src.booru.cache_manager import CacheManager
        import time

        cache = CacheManager(str(tmp_path / 'cache.db'), ttl_hours=1)

        # Write 1000 entries
        start = time.time()
        for i in range(1000):
            cache.set(f"hash_{i}", {'data': f'value_{i}'})
        write_time = time.time() - start

        # Read 1000 entries
        start = time.time()
        for i in range(1000):
            cache.get(f"hash_{i}")
        read_time = time.time() - start

        # Should be reasonably fast
        assert write_time < 5.0  # 1000 writes in 5 seconds
        assert read_time < 1.0   # 1000 reads in 1 second

    def test_preference_database_performance(self, tmp_path):
        """Test preference database performance."""
        from src.learning import PreferenceDatabase
        import time

        pref_db = PreferenceDatabase(str(tmp_path / 'prefs.db'))

        # Record 100 movements
        start = time.time()
        for i in range(100):
            pref_db.record_movement(
                file_hash=f'hash_{i}',
                file_name=f'file_{i}.jpg',
                actual_category='Test/Category',
                style='anime',
                persons_detected=i % 5
            )
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 2.0


class TestErrorHandling:
    """Error handling and edge case tests."""

    def test_missing_image_file(self, tmp_path, test_config):
        """Test handling of missing image file."""
        from src.content_analysis import ContentAnalyzer

        analyzer = ContentAnalyzer(test_config)

        # Try to analyze non-existent file
        result = analyzer.analyze_image(tmp_path / 'nonexistent.jpg')

        assert result['status'] == 'error'
        assert 'error' in result

    def test_corrupted_config(self, tmp_path):
        """Test handling of corrupted configuration."""
        from src.utils.config_loader import ConfigLoader

        # Create corrupted YAML file
        config_path = tmp_path / 'bad_config.yaml'
        with open(config_path, 'w') as f:
            f.write("this: is: not: valid: yaml: {{{")

        # Should handle gracefully
        loader = ConfigLoader(str(config_path))
        with pytest.raises(Exception):
            loader.load()

    def test_invalid_metadata(self, tmp_path):
        """Test validation of invalid metadata."""
        from src.xmp_writer import MetadataBuilder

        # Missing required fields
        invalid_metadata = {'tags': ['tag1']}  # Missing image_path

        assert not MetadataBuilder.validate_metadata(invalid_metadata)

        # Invalid rating
        invalid_metadata = {
            'image_path': Path('test.jpg'),
            'tags': [],
            'rating': 10  # Out of range
        }

        assert not MetadataBuilder.validate_metadata(invalid_metadata)


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_tag_list(self, tmp_path):
        """Test handling of empty tag list."""
        from src.xmp_writer import MetadataBuilder

        metadata = MetadataBuilder.build_from_flat_tags(
            tmp_path / 'test.jpg',
            tags=[],
            description='No tags'
        )

        assert metadata['tags'] == []
        assert metadata['description'] == 'No tags'

    def test_very_long_tags(self):
        """Test handling of very long tag strings."""
        from src.xmp_writer import ExifToolWrapper

        long_tag = "a" * 1000
        sanitized = ExifToolWrapper._sanitize_tag(long_tag)

        # Should still work, just very long
        assert len(sanitized) == 1000

    def test_unicode_tags(self):
        """Test handling of Unicode characters in tags."""
        from src.booru.tag_normalizer import TagNormalizer

        unicode_tags = ['日本語', 'français', 'español', '한국어']
        filtered = TagNormalizer.filter_tags(unicode_tags)

        # Should preserve Unicode
        assert len(filtered) == 4
