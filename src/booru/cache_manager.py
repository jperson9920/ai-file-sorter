"""Cache manager for reverse image search results."""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage caching of reverse search results in SQLite."""

    def __init__(self, db_path: str, ttl_hours: int = 48):
        """Initialize cache manager.

        Args:
            db_path: Path to SQLite database file
            ttl_hours: Time to live for cached entries in hours
        """
        self.db_path = Path(db_path)
        self.ttl_hours = ttl_hours
        self._init_db()
        logger.info(f"Cache manager initialized: {self.db_path} (TTL: {ttl_hours}h)")

    def _init_db(self):
        """Initialize cache database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_cache (
                    image_hash TEXT PRIMARY KEY,
                    result TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_cached_at
                ON search_cache(cached_at)
            ''')
            conn.commit()

    def get(self, image_hash: str) -> Optional[Dict]:
        """Retrieve cached result if not expired.

        Args:
            image_hash: SHA256 hash of the image

        Returns:
            Cached result dictionary or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT result, cached_at FROM search_cache WHERE image_hash = ?',
                (image_hash,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            result_json, cached_at = row

            # Parse timestamp
            try:
                cached_time = datetime.fromisoformat(cached_at)
            except ValueError:
                # Invalid timestamp, treat as expired
                logger.warning(f"Invalid timestamp in cache for {image_hash}")
                return None

            # Check if expired
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                logger.debug(f"Cache entry expired for {image_hash}")
                return None

            try:
                result = json.loads(result_json)
                logger.debug(f"Cache hit for {image_hash}")
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cached JSON for {image_hash}")
                return None

    def set(self, image_hash: str, result: Dict):
        """Cache search result.

        Args:
            image_hash: SHA256 hash of the image
            result: Result dictionary to cache
        """
        try:
            result_json = json.dumps(result)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO search_cache (image_hash, result, cached_at) VALUES (?, ?, ?)',
                    (image_hash, result_json, datetime.now().isoformat())
                )
                conn.commit()
                logger.debug(f"Cached result for {image_hash}")
        except Exception as e:
            logger.error(f"Failed to cache result for {image_hash}: {e}")

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries deleted
        """
        cutoff = datetime.now() - timedelta(hours=self.ttl_hours)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM search_cache WHERE cached_at < ?',
                (cutoff.isoformat(),)
            )
            conn.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired cache entries")
            return deleted

    def get_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and hit information
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM search_cache')
            total_entries = cursor.fetchone()[0]

            cursor = conn.execute(
                'SELECT COUNT(*) FROM search_cache WHERE cached_at >= ?',
                ((datetime.now() - timedelta(hours=self.ttl_hours)).isoformat(),)
            )
            valid_entries = cursor.fetchone()[0]

            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': total_entries - valid_entries,
                'ttl_hours': self.ttl_hours
            }

    def clear_all(self):
        """Clear all cached entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('DELETE FROM search_cache')
            conn.commit()
            deleted = cursor.rowcount
            logger.info(f"Cleared all cache entries ({deleted} deleted)")
            return deleted
