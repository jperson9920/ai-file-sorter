"""Unit tests for Danbooru client."""

import pytest
from src.booru.danbooru_client import DanbooruClient


class TestDanbooruClient:
    """Test cases for DanbooruClient class."""

    @pytest.fixture
    def client(self):
        """Create Danbooru client instance without authentication."""
        return DanbooruClient()

    @pytest.fixture
    def authenticated_client(self):
        """Create authenticated Danbooru client instance."""
        # Note: These are dummy credentials for testing
        return DanbooruClient(username="test_user", api_key="test_key")

    def test_initialization_without_auth(self, client):
        """Test initialization without authentication."""
        assert client.username is None
        assert client.api_key is None
        assert client.client is not None
        assert not client.is_authenticated()

    def test_initialization_with_auth(self, authenticated_client):
        """Test initialization with authentication."""
        assert authenticated_client.username == "test_user"
        assert authenticated_client.api_key == "test_key"
        assert authenticated_client.client is not None
        assert authenticated_client.is_authenticated()

    def test_extract_post_id_standard_url(self, client):
        """Test extracting post ID from standard Danbooru URL."""
        url = "https://danbooru.donmai.us/posts/1234567"
        post_id = client.extract_post_id(url)
        assert post_id == 1234567

    def test_extract_post_id_show_url(self, client):
        """Test extracting post ID from show URL format."""
        url = "https://danbooru.donmai.us/post/show/1234567"
        post_id = client.extract_post_id(url)
        assert post_id == 1234567

    def test_extract_post_id_with_query_params(self, client):
        """Test extracting post ID from URL with query parameters."""
        url = "https://danbooru.donmai.us/posts/1234567?tag=blue_eyes"
        post_id = client.extract_post_id(url)
        assert post_id == 1234567

    def test_extract_post_id_relative_path(self, client):
        """Test extracting post ID from relative path."""
        url = "/posts/1234567"
        post_id = client.extract_post_id(url)
        assert post_id == 1234567

    def test_extract_post_id_id_parameter(self, client):
        """Test extracting post ID from id parameter."""
        url = "https://example.com/post?id=1234567"
        post_id = client.extract_post_id(url)
        assert post_id == 1234567

    def test_extract_post_id_invalid_url(self, client):
        """Test extracting post ID from invalid URL."""
        url = "https://example.com/random/page"
        post_id = client.extract_post_id(url)
        assert post_id is None

    def test_extract_post_id_none(self, client):
        """Test extracting post ID from None."""
        post_id = client.extract_post_id(None)
        assert post_id is None

    def test_extract_post_id_empty_string(self, client):
        """Test extracting post ID from empty string."""
        post_id = client.extract_post_id("")
        assert post_id is None

    def test_get_tags_structure(self, client, monkeypatch):
        """Test that get_tags returns proper structure."""
        # Mock the post_show method
        mock_post = {
            'tag_string_general': 'blue_eyes long_hair school_uniform',
            'tag_string_character': 'hinata_hyuga_(naruto)',
            'tag_string_copyright': 'naruto',
            'tag_string_artist': 'artist_name',
            'rating': 's'
        }

        def mock_post_show(post_id):
            return mock_post

        monkeypatch.setattr(client.client, 'post_show', mock_post_show)

        tags = client.get_tags(12345, max_tags=10)

        assert 'general' in tags
        assert 'characters' in tags
        assert 'series' in tags
        assert 'artists' in tags
        assert 'rating' in tags

        assert tags['general'] == ['blue_eyes', 'long_hair', 'school_uniform']
        assert tags['characters'] == ['hinata_hyuga_(naruto)']
        assert tags['series'] == ['naruto']
        assert tags['artists'] == ['artist_name']
        assert tags['rating'] == 'safe'

    def test_get_tags_rating_mapping(self, client, monkeypatch):
        """Test that rating codes are mapped to full names."""
        test_cases = [
            ('s', 'safe'),
            ('q', 'questionable'),
            ('e', 'explicit'),
            ('g', 'general'),
            ('unknown', 'unknown')
        ]

        for rating_code, expected_name in test_cases:
            mock_post = {
                'tag_string_general': 'tag1',
                'tag_string_character': '',
                'tag_string_copyright': '',
                'tag_string_artist': '',
                'rating': rating_code
            }

            def mock_post_show(post_id):
                return mock_post

            monkeypatch.setattr(client.client, 'post_show', mock_post_show)

            tags = client.get_tags(12345)
            assert tags['rating'] == expected_name

    def test_get_tags_max_tags_limit(self, client, monkeypatch):
        """Test that max_tags parameter limits general tags."""
        mock_post = {
            'tag_string_general': 'tag1 tag2 tag3 tag4 tag5 tag6 tag7 tag8 tag9 tag10',
            'tag_string_character': '',
            'tag_string_copyright': '',
            'tag_string_artist': '',
            'rating': 's'
        }

        def mock_post_show(post_id):
            return mock_post

        monkeypatch.setattr(client.client, 'post_show', mock_post_show)

        # Test with max_tags=5
        tags = client.get_tags(12345, max_tags=5)
        assert len(tags['general']) == 5
        assert tags['general'] == ['tag1', 'tag2', 'tag3', 'tag4', 'tag5']

    def test_get_tags_from_url_success(self, client, monkeypatch):
        """Test get_tags_from_url with valid URL."""
        mock_post = {
            'tag_string_general': 'blue_eyes',
            'tag_string_character': '',
            'tag_string_copyright': '',
            'tag_string_artist': '',
            'rating': 's'
        }

        def mock_post_show(post_id):
            return mock_post

        monkeypatch.setattr(client.client, 'post_show', mock_post_show)

        url = "https://danbooru.donmai.us/posts/12345"
        tags = client.get_tags_from_url(url, max_tags=10)

        assert tags is not None
        assert tags['general'] == ['blue_eyes']

    def test_get_tags_from_url_invalid(self, client):
        """Test get_tags_from_url with invalid URL."""
        url = "https://example.com/not/a/danbooru/url"
        tags = client.get_tags_from_url(url)

        assert tags is None

    def test_get_tags_empty_strings(self, client, monkeypatch):
        """Test handling of empty tag strings."""
        mock_post = {
            'tag_string_general': '',
            'tag_string_character': '',
            'tag_string_copyright': '',
            'tag_string_artist': '',
            'rating': 's'
        }

        def mock_post_show(post_id):
            return mock_post

        monkeypatch.setattr(client.client, 'post_show', mock_post_show)

        tags = client.get_tags(12345)

        assert tags['general'] == []
        assert tags['characters'] == []
        assert tags['series'] == []
        assert tags['artists'] == []
