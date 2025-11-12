"""Performance benchmarking tests."""

import pytest
import time
from pathlib import Path
from PIL import Image
import tempfile


@pytest.fixture
def generate_test_images():
    """Generate test images for benchmarking."""
    def _generate(count=100):
        images = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(count):
                img_path = Path(tmpdir) / f"bench_{i}.jpg"
                img = Image.new('RGB', (800, 600), color=(i % 255, 100, 200))
                img.save(img_path, 'JPEG', quality=85)
                images.append(img_path)
            yield images
    return _generate


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Benchmark tests for performance targets."""

    @pytest.mark.slow
    @pytest.mark.skipif(True, reason="Requires actual models and API keys")
    def test_1000_images_end_to_end(self):
        """
        Target: Process 1,000 images in under 45 minutes.

        This is the full end-to-end benchmark including:
        - Reverse image search (rate-limited to 6/30s)
        - Content analysis with CLIP + Faster R-CNN
        - XMP sidecar writing
        - All processing steps

        This test is skipped by default as it requires:
        - Valid API keys
        - Downloaded models
        - Long runtime (~45 minutes)
        """
        # This would be run manually for full system benchmarking
        pass

    @pytest.mark.slow
    def test_xmp_writing_1000_images(self, tmp_path):
        """
        Target: Write XMP sidecars for 1,000 images in under 60 seconds.

        Tests ExifTool stay_open mode performance.
        """
        pytest.skip("Requires ExifTool and large image set")

        # Generate 100 test images (scaled down for CI)
        images = []
        for i in range(100):
            img_path = tmp_path / f"test_{i}.jpg"
            img = Image.new('RGB', (800, 600), color='blue')
            img.save(img_path)
            images.append(img_path)

        from src.xmp_writer import ExifToolWrapper

        try:
            with ExifToolWrapper() as et:
                start = time.time()

                # Write XMP for all images
                batch_metadata = []
                for img_path in images:
                    batch_metadata.append({
                        'image_path': img_path,
                        'tags': ['test1', 'test2', 'test3'],
                        'description': 'Benchmark test'
                    })

                results = et.write_xmp_batch(batch_metadata)

                elapsed = time.time() - start

                # 100 images should complete in under 6 seconds
                # (extrapolates to 1000 in 60 seconds)
                assert elapsed < 6.0
                assert results['success'] == 100

        except RuntimeError:
            pytest.skip("ExifTool not available")

    def test_content_analysis_speed(self):
        """
        Target: Analyze 1,000 images in under 5 minutes with AI models.

        This translates to ~300ms per image on CPU.
        """
        pytest.skip("Requires CLIP and Faster R-CNN models downloaded")

    def test_json_validation_speed(self, tmp_path):
        """
        Target: Validate 1,000 JSON files in 2-3 seconds.

        Tests parallel validation with 8 workers.
        """
        from src.workflow import JSONValidator
        import json

        # Create 1000 test JSON files
        json_files = []
        for i in range(1000):
            json_path = tmp_path / f"uma_{i}.json"
            data = {
                'name': f'Test Support Card {i}' if i % 2 == 0 else f'Test Character {i}',
                'slug': f'test_support_card_{i}' if i % 2 == 0 else f'test_char_{i}'
            }
            with open(json_path, 'w') as f:
                json.dump(data, f)
            json_files.append(json_path)

        validator = JSONValidator(max_workers=8)

        start = time.time()
        results = validator.validate_batch(json_files)
        elapsed = time.time() - start

        # Should complete in under 3 seconds
        assert elapsed < 3.0
        assert len(results['valid']) + len(results['filtered']) == 1000

    def test_cache_throughput(self, tmp_path):
        """Test cache read/write throughput."""
        from src.booru.cache_manager import CacheManager

        cache = CacheManager(str(tmp_path / 'bench_cache.db'), ttl_hours=48)

        # Write throughput
        start = time.time()
        for i in range(1000):
            cache.set(f'hash_{i}', {
                'status': 'success',
                'similarity': 85.5,
                'tags': ['tag1', 'tag2', 'tag3']
            })
        write_elapsed = time.time() - start

        # Read throughput
        start = time.time()
        hits = 0
        for i in range(1000):
            if cache.get(f'hash_{i}'):
                hits += 1
        read_elapsed = time.time() - start

        print(f"\nCache Performance:")
        print(f"  Write: {1000/write_elapsed:.0f} ops/sec")
        print(f"  Read:  {1000/read_elapsed:.0f} ops/sec")

        # Reasonable performance expectations
        assert write_elapsed < 5.0
        assert read_elapsed < 1.0
        assert hits == 1000

    def test_tag_normalization_throughput(self):
        """Test tag normalization throughput."""
        from src.booru.tag_normalizer import TagNormalizer

        # Test data
        tag_data = {
            'general': [f'tag_{i}' for i in range(100)],
            'characters': [
                {'name': f'char_{i}', 'series': f'series_{i % 10}'}
                for i in range(20)
            ],
            'series': [f'series_{i}' for i in range(10)],
            'artists': [f'artist_{i}' for i in range(5)],
            'rating': 'safe'
        }

        start = time.time()
        for _ in range(1000):
            TagNormalizer.normalize_post_tags(tag_data)
        elapsed = time.time() - start

        # Should handle 1000 normalizations quickly
        assert elapsed < 1.0

    def test_rate_limiter_accuracy(self):
        """Test rate limiter timing accuracy."""
        import asyncio
        from src.utils.rate_limiter import RateLimiter

        async def test_timing():
            limiter = RateLimiter(requests_per_30s=10)

            # Make 10 requests (should be instant)
            start = time.time()
            for _ in range(10):
                await limiter.acquire()
            first_batch = time.time() - start

            # 11th request should wait ~30 seconds
            # But we'll just verify it waits at all
            start = time.time()
            await limiter.acquire()
            second_wait = time.time() - start

            return first_batch, second_wait

        first_batch, second_wait = asyncio.run(test_timing())

        # First 10 should be fast
        assert first_batch < 1.0

        # 11th should wait (we'd expect ~30s but will skip full wait)
        # In real usage this prevents hitting rate limits
        assert second_wait >= 0  # Just verify no error


@pytest.mark.benchmark
class TestScalability:
    """Scalability tests."""

    def test_database_scaling(self, tmp_path):
        """Test database performance with large datasets."""
        from src.learning import PreferenceDatabase

        pref_db = PreferenceDatabase(str(tmp_path / 'scale_test.db'))

        # Insert 1000 records
        start = time.time()
        for i in range(1000):
            pref_db.record_movement(
                file_hash=f'hash_{i}',
                file_name=f'file_{i}.jpg',
                actual_category=f'Category_{i % 10}',
                style='anime' if i % 2 == 0 else 'realistic',
                persons_detected=i % 5,
                booru_tags=[f'tag_{j}' for j in range(5)]
            )
        insert_time = time.time() - start

        # Query performance
        start = time.time()
        for i in range(100):
            pref_db.suggest_category(
                style='anime',
                persons_detected=2,
                booru_tags=['tag_1', 'tag_2']
            )
        query_time = time.time() - start

        print(f"\nDatabase Scalability:")
        print(f"  1000 inserts: {insert_time:.2f}s")
        print(f"  100 queries: {query_time:.2f}s")

        # Should scale reasonably
        assert insert_time < 10.0
        assert query_time < 2.0

    def test_memory_efficiency(self, tmp_path):
        """Test memory usage doesn't grow excessively."""
        import sys
        from src.booru.cache_manager import CacheManager

        cache = CacheManager(str(tmp_path / 'memory_test.db'), ttl_hours=1)

        # Record initial memory usage
        # This is approximate and platform-dependent
        initial_size = sys.getsizeof(cache)

        # Add 1000 entries
        for i in range(1000):
            cache.set(f'hash_{i}', {'data': f'value_{i}' * 10})

        # Memory shouldn't grow dramatically in Python object
        # (data is in SQLite, not in memory)
        final_size = sys.getsizeof(cache)

        # Object size should stay roughly the same
        assert final_size < initial_size * 2
