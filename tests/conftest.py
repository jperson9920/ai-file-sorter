"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return {
        'directories': {
            'inbox': 'C:\\ImageProcessing\\Inbox',
            'sorted': 'C:\\ImageProcessing\\Sorted',
            'working': 'C:\\ImageProcessing\\Working'
        },
        'api': {
            'saucenao': {
                'api_key': 'test_saucenao_key',
                'rate_limit': 6,
                'min_similarity': 70.0
            },
            'danbooru': {
                'username': 'test_user',
                'api_key': 'test_danbooru_key'
            },
            'iqdb': {
                'enabled': True,
                'min_similarity': 80.0
            }
        },
        'content_analysis': {
            'enabled': True
        },
        'xmp': {
            'exiftool_path': '',
            'sidecar_format': '{filename}.xmp'
        },
        'learning': {
            'database_path': 'data/preferences.db',
            'min_confidence': 0.7,
            'min_samples': 50
        },
        'workflow': {
            'batch_size': 100,
            'parallel_workers': 4
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/test.log',
            'console_output': False
        },
        'performance': {
            'cache_enabled': True,
            'cache_ttl_hours': 48
        }
    }


@pytest.fixture
def mock_danbooru_post():
    """Provide a mock Danbooru post response."""
    return {
        'id': 12345,
        'tag_string_general': 'blue_eyes long_hair school_uniform smile',
        'tag_string_character': 'hinata_hyuga_(naruto) sakura_haruno_(naruto)',
        'tag_string_copyright': 'naruto',
        'tag_string_artist': 'artist_name',
        'rating': 's',
        'file_url': 'https://example.com/image.jpg'
    }


@pytest.fixture
def mock_saucenao_result():
    """Provide a mock SauceNAO search result."""
    return {
        'status': 'success',
        'similarity': 95.5,
        'url': 'https://danbooru.donmai.us/posts/12345',
        'site': 'Danbooru',
        'thumbnail': 'https://example.com/thumb.jpg'
    }
