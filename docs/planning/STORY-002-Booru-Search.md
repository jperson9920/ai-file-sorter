# STORY-002: Booru Reverse Image Search Implementation

**Epic:** EPIC-001
**Story Points:** 5
**Priority:** P0 - Critical
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 2-3 days

## User Story

As a **user**, I want to **automatically find existing tags for my anime images using reverse image search** so that **I can leverage human-curated tags from booru databases instead of manually tagging thousands of images**.

## Acceptance Criteria

### AC1: SauceNAO Integration
- [ ] Implement async SauceNAO client using `saucenao-api` library
- [ ] Support both URL and file path inputs
- [ ] Return similarity score, source URL, and matched site
- [ ] Handle API rate limits (6 requests per 30 seconds)
- [ ] Implement exponential backoff on 429 rate limit errors
- [ ] Cache results using image hash to avoid duplicate searches

### AC2: IQDB Backup Search
- [ ] Implement IQDB client using `PicImageSearch` library
- [ ] Automatically fallback to IQDB when SauceNAO fails
- [ ] Parse HTML response to extract match data
- [ ] Return consistent result format matching SauceNAO output

### AC3: Danbooru Tag Extraction
- [ ] Implement Danbooru client using `pybooru` library
- [ ] Extract post ID from SauceNAO/IQDB result URLs
- [ ] Retrieve post details via Danbooru API
- [ ] Parse tag categories: general, character, copyright, artist
- [ ] Return top 10 general tags ranked by popularity
- [ ] Include character tags with series information

### AC4: Tag Normalization
- [ ] Convert booru format to human-readable tags
  - `blue_eyes` → "blue eyes"
  - `hinata_hyuga_(naruto)` → "Hinata Hyuga" + "Naruto" series
- [ ] Filter out rating tags (safe/questionable/explicit)
- [ ] Remove meta tags (translation_request, commentary, etc.)
- [ ] Capitalize proper nouns (character names, series titles)

### AC5: Result Caching
- [ ] Implement SHA256 image hashing
- [ ] Store results in SQLite cache database
- [ ] Cache TTL of 48 hours (configurable)
- [ ] Skip API calls for cached images
- [ ] Provide cache statistics (hit rate, size)

### AC6: Error Handling
- [ ] Handle network timeouts gracefully
- [ ] Retry failed requests with exponential backoff (max 3 attempts)
- [ ] Log all API errors with context
- [ ] Return partial results when possible
- [ ] Provide meaningful error messages to user

## Technical Implementation

### Class Structure

```python
# src/booru/saucenao_client.py
import asyncio
from saucenao_api import AIOSauceNao
from typing import Optional, Dict, List
import hashlib
from pathlib import Path

class SauceNAOClient:
    def __init__(self, api_key: Optional[str], cache_manager):
        self.api_key = api_key
        self.sauce = AIOSauceNao(api_key=api_key)
        self.cache = cache_manager
        self.rate_limiter = RateLimiter(requests_per_30s=6)

    async def search_image(self, image_path: Path, min_similarity: float = 70.0) -> Dict:
        """Search for image and return best match."""
        # Check cache first
        image_hash = self._hash_image(image_path)
        cached = self.cache.get(image_hash)
        if cached:
            return cached

        # Rate limiting
        await self.rate_limiter.acquire()

        try:
            results = await self.sauce.from_file(str(image_path))

            if not results or results[0].similarity < min_similarity:
                return {'status': 'no_match', 'similarity': 0}

            best_match = results[0]
            result = {
                'status': 'success',
                'similarity': best_match.similarity,
                'url': best_match.urls[0] if best_match.urls else None,
                'site': best_match.index_name,
                'thumbnail': best_match.thumbnail
            }

            # Cache result
            self.cache.set(image_hash, result)
            return result

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _hash_image(self, image_path: Path) -> str:
        """Generate SHA256 hash of image file."""
        sha256 = hashlib.sha256()
        with open(image_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
```

```python
# src/booru/danbooru_client.py
from pybooru import Danbooru
from typing import List, Dict
import re

class DanbooruClient:
    def __init__(self, username: str, api_key: str):
        self.client = Danbooru('danbooru', username=username, api_key=api_key)

    def extract_post_id(self, url: str) -> Optional[int]:
        """Extract post ID from Danbooru URL."""
        patterns = [
            r'danbooru\.donmai\.us/posts/(\d+)',
            r'danbooru\.donmai\.us/post/show/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(1))
        return None

    def get_tags(self, post_id: int, max_tags: int = 10) -> Dict[str, List[str]]:
        """Retrieve tags for a post."""
        try:
            post = self.client.post_show(post_id)

            # Extract different tag categories
            general_tags = post.get('tag_string_general', '').split()[:max_tags]
            character_tags = post.get('tag_string_character', '').split()
            copyright_tags = post.get('tag_string_copyright', '').split()
            artist_tags = post.get('tag_string_artist', '').split()

            return {
                'general': general_tags,
                'characters': character_tags,
                'series': copyright_tags,
                'artists': artist_tags,
                'rating': post.get('rating', 'unknown')
            }
        except Exception as e:
            raise Exception(f"Failed to fetch tags for post {post_id}: {e}")
```

```python
# src/booru/tag_normalizer.py
import re
from typing import List, Dict

class TagNormalizer:
    """Normalize booru tags to human-readable format."""

    # Tags to always filter out
    FILTER_TAGS = {
        'translation_request', 'commentary', 'commentary_request',
        'bad_id', 'bad_link', 'md5_mismatch', 'annotated'
    }

    RATING_TAGS = {'safe', 'questionable', 'explicit', 'sensitive'}

    @staticmethod
    def normalize_general_tag(tag: str) -> str:
        """Convert booru format to readable: blue_eyes -> Blue Eyes"""
        # Replace underscores with spaces
        readable = tag.replace('_', ' ')
        # Capitalize each word
        return readable.title()

    @staticmethod
    def normalize_character_tag(tag: str) -> Dict[str, str]:
        """Parse character tag: hinata_hyuga_(naruto) -> name + series"""
        # Pattern: character_name_(series_name)
        match = re.match(r'(.+?)_\((.+?)\)', tag)
        if match:
            name = match.group(1).replace('_', ' ').title()
            series = match.group(2).replace('_', ' ').title()
            return {'name': name, 'series': series}
        else:
            # No series in parentheses
            return {'name': tag.replace('_', ' ').title(), 'series': None}

    @staticmethod
    def filter_tags(tags: List[str]) -> List[str]:
        """Remove meta tags and unwanted tags."""
        filtered = []
        for tag in tags:
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
            filtered.append(tag)
        return filtered

    @classmethod
    def normalize_post_tags(cls, tag_data: Dict) -> Dict:
        """Normalize all tags from a post."""
        general = [cls.normalize_general_tag(t)
                   for t in cls.filter_tags(tag_data.get('general', []))]

        characters = [cls.normalize_character_tag(t)
                      for t in tag_data.get('characters', [])]

        series = [s.replace('_', ' ').title()
                  for s in tag_data.get('series', [])]

        artists = [a.replace('_', ' ').title()
                   for a in tag_data.get('artists', [])]

        return {
            'general': general,
            'characters': characters,
            'series': series,
            'artists': artists,
            'rating': tag_data.get('rating', 'unknown')
        }
```

```python
# src/booru/iqdb_client.py
from PicImageSearch import Iqdb
from typing import Optional, Dict

class IQDBClient:
    """Fallback search client using IQDB."""

    def __init__(self):
        self.client = Iqdb()

    async def search_image(self, image_path: str, min_similarity: float = 80.0) -> Dict:
        """Search IQDB for similar images."""
        try:
            result = await self.client.search(file=image_path)

            if not result.raw:
                return {'status': 'no_match', 'similarity': 0}

            # Get best match
            best_match = result.raw[0]
            similarity = float(best_match.similarity)

            if similarity < min_similarity:
                return {'status': 'no_match', 'similarity': similarity}

            return {
                'status': 'success',
                'similarity': similarity,
                'url': best_match.url,
                'site': 'IQDB',
                'thumbnail': best_match.thumbnail
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
```

```python
# src/booru/cache_manager.py
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

class CacheManager:
    """Manage caching of reverse search results."""

    def __init__(self, db_path: str, ttl_hours: int = 48):
        self.db_path = Path(db_path)
        self.ttl_hours = ttl_hours
        self._init_db()

    def _init_db(self):
        """Initialize cache database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_cache (
                    image_hash TEXT PRIMARY KEY,
                    result JSON NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_cached_at
                ON search_cache(cached_at)
            ''')

    def get(self, image_hash: str) -> Optional[Dict]:
        """Retrieve cached result if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT result, cached_at FROM search_cache WHERE image_hash = ?',
                (image_hash,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            result_json, cached_at = row
            cached_time = datetime.fromisoformat(cached_at)

            # Check if expired
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                return None

            return json.loads(result_json)

    def set(self, image_hash: str, result: Dict):
        """Cache search result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO search_cache (image_hash, result) VALUES (?, ?)',
                (image_hash, json.dumps(result))
            )

    def cleanup_expired(self):
        """Remove expired cache entries."""
        cutoff = datetime.now() - timedelta(hours=self.ttl_hours)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'DELETE FROM search_cache WHERE cached_at < ?',
                (cutoff.isoformat(),)
            )
```

### Rate Limiter Implementation

```python
# src/utils/rate_limiter.py
import asyncio
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self, requests_per_30s: int = 6):
        self.max_requests = requests_per_30s
        self.window = timedelta(seconds=30)
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        async with self.lock:
            now = datetime.now()

            # Remove requests outside window
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()

            # Wait if at limit
            if len(self.requests) >= self.max_requests:
                sleep_time = (self.requests[0] + self.window - now).total_seconds()
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time + 0.1)  # Small buffer

            self.requests.append(now)
```

## Testing Strategy

### Unit Tests

```python
# tests/test_booru/test_tag_normalizer.py
def test_normalize_general_tag():
    assert TagNormalizer.normalize_general_tag("blue_eyes") == "Blue Eyes"
    assert TagNormalizer.normalize_general_tag("long_hair") == "Long Hair"

def test_normalize_character_tag():
    result = TagNormalizer.normalize_character_tag("hinata_hyuga_(naruto)")
    assert result['name'] == "Hinata Hyuga"
    assert result['series'] == "Naruto"

def test_filter_tags():
    tags = ["blue_eyes", "translation_request", "ab", "123", "long_hair"]
    filtered = TagNormalizer.filter_tags(tags)
    assert "blue_eyes" in filtered
    assert "long_hair" in filtered
    assert "translation_request" not in filtered
    assert "ab" not in filtered
    assert "123" not in filtered
```

### Integration Tests
- [ ] Test SauceNAO API with real image (requires API key)
- [ ] Test Danbooru tag extraction with known post ID
- [ ] Test cache hit/miss scenarios
- [ ] Test rate limiter with rapid requests
- [ ] Test fallback from SauceNAO to IQDB

### Manual Testing
- [ ] Test with 100 sample anime images
- [ ] Verify match rate is 70%+ for anime artwork
- [ ] Confirm realistic photos have <5% match rate
- [ ] Test rate limit handling (wait times, no 429 errors)
- [ ] Verify cache reduces API calls on reruns

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests pass with 85%+ coverage
- [ ] Integration tests pass with real API
- [ ] Logging implemented for all API calls
- [ ] Error handling covers all edge cases
- [ ] Configuration options documented
- [ ] Code reviewed and approved
- [ ] Manual testing completed with 100 images
- [ ] Performance meets target (6 req/30s sustained)

## Dependencies

**Depends On:**
- STORY-001 (Project setup for configuration and logging)

**Blocks:**
- STORY-008 (Workflow orchestration needs reverse search)

## Notes

- Free tier SauceNAO allows 200 searches/day
- Danbooru API requires account (free registration)
- Consider paid SauceNAO tier for >200/day ($5-20/month)
- IQDB has no official API - scraping may break
- Cache dramatically reduces API usage on reruns

## Risks

- **Medium Risk:** API rate limits may throttle batch processing
  - *Mitigation:* Implement queue system, process overnight

- **Low Risk:** IQDB HTML parsing may break on site updates
  - *Mitigation:* Implement robust error handling, update library

## Related Files

- `/src/booru/saucenao_client.py`
- `/src/booru/iqdb_client.py`
- `/src/booru/danbooru_client.py`
- `/src/booru/tag_normalizer.py`
- `/src/booru/cache_manager.py`
- `/src/utils/rate_limiter.py`
- `/tests/test_booru/`

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
