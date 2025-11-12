"""Unit tests for ExifTool wrapper."""

import pytest
from pathlib import Path
from src.xmp_writer.exiftool_wrapper import ExifToolWrapper


class TestExifToolWrapper:
    """Test cases for ExifToolWrapper class."""

    def test_sanitize_tag_whitespace(self):
        """Test tag sanitization removes extra whitespace."""
        assert ExifToolWrapper._sanitize_tag("  blue eyes  ") == "blue eyes"
        assert ExifToolWrapper._sanitize_tag("blue   eyes") == "blue eyes"
        assert ExifToolWrapper._sanitize_tag("\tblue\teyes\t") == "blue eyes"

    def test_sanitize_tag_empty(self):
        """Test sanitization of empty strings."""
        assert ExifToolWrapper._sanitize_tag("") == ""
        assert ExifToolWrapper._sanitize_tag("   ") == ""
        assert ExifToolWrapper._sanitize_tag(None) == ""

    def test_sanitize_tag_control_characters(self):
        """Test sanitization removes control characters."""
        # ASCII control characters (0-31) should be removed
        tag_with_controls = "blue\x00eyes\x01test\x1f"
        sanitized = ExifToolWrapper._sanitize_tag(tag_with_controls)
        assert sanitized == "blue eyes test"

    def test_sanitize_tag_normal_text(self):
        """Test that normal tags pass through unchanged."""
        assert ExifToolWrapper._sanitize_tag("blue eyes") == "blue eyes"
        assert ExifToolWrapper._sanitize_tag("long hair") == "long hair"
        assert ExifToolWrapper._sanitize_tag("School-Uniform_2023") == "School-Uniform_2023"

    def test_sanitize_text_whitespace(self):
        """Test text sanitization normalizes whitespace."""
        assert ExifToolWrapper._sanitize_text("  test  ") == "test"
        assert ExifToolWrapper._sanitize_text("test\n\ntest") == "test test"
        assert ExifToolWrapper._sanitize_text("a    b    c") == "a b c"

    def test_sanitize_text_empty(self):
        """Test sanitization of empty text."""
        assert ExifToolWrapper._sanitize_text("") == ""
        assert ExifToolWrapper._sanitize_text("   ") == ""
        assert ExifToolWrapper._sanitize_text(None) == ""

    def test_sanitize_text_preserves_content(self):
        """Test that normal text content is preserved."""
        text = "This is a test description with some content."
        assert ExifToolWrapper._sanitize_text(text) == text

    def test_validate_xmp_valid(self, tmp_path):
        """Test validation of valid XMP file."""
        xmp_path = tmp_path / "valid.xmp"
        xmp_path.write_text('<?xml version="1.0"?><root><tag>value</tag></root>')

        assert ExifToolWrapper._validate_xmp(xmp_path) is True

    def test_validate_xmp_invalid(self, tmp_path):
        """Test validation of invalid XMP file."""
        xmp_path = tmp_path / "invalid.xmp"
        xmp_path.write_text('<root><unclosed>')

        assert ExifToolWrapper._validate_xmp(xmp_path) is False

    def test_validate_xmp_empty(self, tmp_path):
        """Test validation of empty XMP file."""
        xmp_path = tmp_path / "empty.xmp"
        xmp_path.write_text('')

        assert ExifToolWrapper._validate_xmp(xmp_path) is False

    def test_validate_xmp_nonexistent(self, tmp_path):
        """Test validation of non-existent XMP file."""
        xmp_path = tmp_path / "nonexistent.xmp"

        assert ExifToolWrapper._validate_xmp(xmp_path) is False

    def test_validate_xmp_complex(self, tmp_path):
        """Test validation of complex but valid XMP structure."""
        xmp_content = '''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/">
      <dc:subject>
        <rdf:Bag>
          <rdf:li>tag1</rdf:li>
          <rdf:li>tag2</rdf:li>
        </rdf:Bag>
      </dc:subject>
      <xmp:Rating>5</xmp:Rating>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''

        xmp_path = tmp_path / "complex.xmp"
        xmp_path.write_text(xmp_content)

        assert ExifToolWrapper._validate_xmp(xmp_path) is True


class TestExifToolWrapperIntegration:
    """Integration tests requiring ExifTool to be installed."""

    @pytest.fixture
    def skip_if_no_exiftool(self):
        """Skip test if ExifTool is not available."""
        try:
            wrapper = ExifToolWrapper()
            return wrapper
        except RuntimeError:
            pytest.skip("ExifTool not installed")

    def test_initialization(self, skip_if_no_exiftool):
        """Test ExifTool wrapper initialization."""
        wrapper = skip_if_no_exiftool
        assert wrapper is not None
        assert wrapper.exiftool_path is None or isinstance(wrapper.exiftool_path, str)

    def test_context_manager(self, skip_if_no_exiftool):
        """Test using ExifTool wrapper as context manager."""
        wrapper = skip_if_no_exiftool

        with wrapper as et:
            assert et.et is not None

        # Should be terminated after context
        assert wrapper.et is None

    def test_write_xmp_without_start(self, skip_if_no_exiftool, tmp_path):
        """Test that writing fails when ExifTool is not started."""
        wrapper = skip_if_no_exiftool

        # Don't start ExifTool
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b'fake image data')

        result = wrapper.write_xmp_sidecar(
            test_image,
            tags=['test'],
        )

        # Should fail because ExifTool not started
        assert result is False

    def test_batch_write_results_structure(self, skip_if_no_exiftool):
        """Test that batch write returns correct result structure."""
        wrapper = skip_if_no_exiftool

        # Test with empty list (doesn't require actual ExifTool execution)
        results = wrapper.write_xmp_batch([])

        assert 'success' in results
        assert 'failed' in results
        assert 'total' in results
        assert results['total'] == 0
        assert results['success'] == 0
        assert results['failed'] == 0
