"""Unit tests for cache manager."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from src.booru.cache_manager import CacheManager


class TestCacheManager:
    """Test cases for CacheManager class."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            yield str(db_path)

    @pytest.fixture
    def cache_manager(self, temp_db):
        """Create cache manager instance."""
        return CacheManager(temp_db, ttl_hours=1)

    def test_initialization(self, temp_db):
        """Test cache manager initialization."""
        cache = CacheManager(temp_db, ttl_hours=24)
        assert cache.db_path.exists()
        assert cache.ttl_hours == 24

    def test_set_and_get(self, cache_manager):
        """Test setting and getting cache entries."""
        test_hash = "abc123"
        test_result = {
            'status': 'success',
            'similarity': 95.5,
            'url': 'https://example.com/post/123'
        }

        # Set cache entry
        cache_manager.set(test_hash, test_result)

        # Get cache entry
        cached = cache_manager.get(test_hash)

        assert cached is not None
        assert cached['status'] == 'success'
        assert cached['similarity'] == 95.5
        assert cached['url'] == 'https://example.com/post/123'

    def test_get_nonexistent(self, cache_manager):
        """Test getting nonexistent cache entry."""
        result = cache_manager.get("nonexistent_hash")
        assert result is None

    def test_cache_overwrite(self, cache_manager):
        """Test overwriting existing cache entry."""
        test_hash = "abc123"

        # First entry
        cache_manager.set(test_hash, {'status': 'success', 'similarity': 90})

        # Overwrite
        cache_manager.set(test_hash, {'status': 'no_match', 'similarity': 50})

        # Should get the new value
        cached = cache_manager.get(test_hash)
        assert cached['status'] == 'no_match'
        assert cached['similarity'] == 50

    def test_cache_expiration(self, temp_db):
        """Test that expired cache entries return None."""
        # Create cache with very short TTL
        cache = CacheManager(temp_db, ttl_hours=0)  # 0 hours = immediate expiration

        test_hash = "abc123"
        test_result = {'status': 'success'}

        # Set cache entry
        cache.set(test_hash, test_result)

        # Should be expired immediately with 0 TTL
        cached = cache.get(test_hash)
        assert cached is None

    def test_cleanup_expired(self, temp_db):
        """Test cleanup of expired entries."""
        cache = CacheManager(temp_db, ttl_hours=1)

        # Add some entries
        cache.set("hash1", {'status': 'success'})
        cache.set("hash2", {'status': 'no_match'})
        cache.set("hash3", {'status': 'success'})

        # Check all exist
        assert cache.get("hash1") is not None
        assert cache.get("hash2") is not None
        assert cache.get("hash3") is not None

        # Change TTL to 0 to make all expired
        cache.ttl_hours = 0

        # Cleanup
        deleted = cache.cleanup_expired()

        # All should be deleted
        assert deleted == 3

        # Verify they're gone
        cache.ttl_hours = 1  # Reset TTL
        assert cache.get("hash1") is None
        assert cache.get("hash2") is None
        assert cache.get("hash3") is None

    def test_get_stats(self, cache_manager):
        """Test cache statistics."""
        # Add some entries
        cache_manager.set("hash1", {'status': 'success'})
        cache_manager.set("hash2", {'status': 'no_match'})
        cache_manager.set("hash3", {'status': 'success'})

        stats = cache_manager.get_stats()

        assert stats['total_entries'] == 3
        assert stats['valid_entries'] == 3
        assert stats['expired_entries'] == 0
        assert stats['ttl_hours'] == 1

    def test_clear_all(self, cache_manager):
        """Test clearing all cache entries."""
        # Add some entries
        cache_manager.set("hash1", {'status': 'success'})
        cache_manager.set("hash2", {'status': 'no_match'})
        cache_manager.set("hash3", {'status': 'success'})

        # Clear all
        deleted = cache_manager.clear_all()
        assert deleted == 3

        # Verify empty
        stats = cache_manager.get_stats()
        assert stats['total_entries'] == 0

    def test_complex_data_structures(self, cache_manager):
        """Test caching complex nested data structures."""
        test_hash = "complex_hash"
        complex_result = {
            'status': 'success',
            'similarity': 95.5,
            'tags': {
                'general': ['blue_eyes', 'long_hair'],
                'characters': [
                    {'name': 'Character 1', 'series': 'Series A'},
                    {'name': 'Character 2', 'series': 'Series B'}
                ],
                'series': ['Series A', 'Series B'],
                'rating': 'safe'
            },
            'metadata': {
                'source': 'danbooru',
                'post_id': 12345,
                'nested': {
                    'deep': {
                        'value': 'test'
                    }
                }
            }
        }

        # Set and get
        cache_manager.set(test_hash, complex_result)
        cached = cache_manager.get(test_hash)

        # Verify structure is preserved
        assert cached['status'] == 'success'
        assert cached['similarity'] == 95.5
        assert len(cached['tags']['general']) == 2
        assert cached['tags']['characters'][0]['name'] == 'Character 1'
        assert cached['metadata']['nested']['deep']['value'] == 'test'
