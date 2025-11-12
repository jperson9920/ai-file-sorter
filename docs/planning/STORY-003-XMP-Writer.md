# STORY-003: XMP Sidecar Writer with ExifTool Integration

**Epic:** EPIC-001
**Story Points:** 3
**Priority:** P0 - Critical
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 1-2 days

## User Story

As a **user**, I want to **write metadata tags to XMP sidecar files** so that **my original images remain unmodified and Immich can automatically read the tags for searchability**.

## Acceptance Criteria

### AC1: ExifTool Integration
- [ ] Detect ExifTool executable on Windows (PATH or configured location)
- [ ] Initialize PyExifTool in stay_open mode for batch performance
- [ ] Handle ExifTool process lifecycle (start, keep alive, shutdown)
- [ ] Verify ExifTool version compatibility (11.0+)

### AC2: XMP Sidecar Creation
- [ ] Generate XMP sidecars with format `image.jpg.xmp` (primary) or `image.xmp` (fallback)
- [ ] Write to `XMP-digiKam:TagsList` field (Immich's primary tag source)
- [ ] Also write to `IPTC:Keywords` and `XMP-dc:Subject` for compatibility
- [ ] Support hierarchical tags with `/` separator (e.g., "Anime/Naruto/Hinata")
- [ ] Never modify original image files

### AC3: Metadata Fields Support
- [ ] **Tags:** Write to digiKam:TagsList, IPTC:Keywords, dc:Subject
- [ ] **Description:** Write to XMP-dc:Description
- [ ] **Rating:** Write to XMP-xmp:Rating (0-5 stars)
- [ ] **DateTime:** Preserve or update DateTimeOriginal
- [ ] **Source:** Write original URL to XMP-dc:Source

### AC4: Batch Performance
- [ ] Process 1,000 images in under 60 seconds using stay_open mode
- [ ] Queue writes and execute in batches
- [ ] Progress reporting (images processed, time remaining)
- [ ] Error recovery - continue on single file failures

### AC5: Validation
- [ ] Verify XMP file created successfully
- [ ] Validate XMP is well-formed XML
- [ ] Check that Immich-required fields are present
- [ ] Log warnings for invalid tag characters

## Technical Implementation

### XMP Writer Class

```python
# src/xmp_writer/exiftool_wrapper.py
import exiftool
from pathlib import Path
from typing import List, Dict, Optional
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class ExifToolWrapper:
    """Wrapper for ExifTool with stay_open mode for performance."""

    def __init__(self, exiftool_path: Optional[str] = None):
        """Initialize ExifTool wrapper.

        Args:
            exiftool_path: Path to exiftool.exe. If None, searches PATH.
        """
        self.exiftool_path = exiftool_path
        self.et = None
        self._verify_exiftool()

    def _verify_exiftool(self):
        """Verify ExifTool is available and compatible version."""
        try:
            # Test ExifTool availability
            with exiftool.ExifTool(executable_=self.exiftool_path) as et:
                version = et.execute('-ver')
                logger.info(f"ExifTool version: {version}")

                # Check minimum version
                version_num = float(version)
                if version_num < 11.0:
                    logger.warning(f"ExifTool {version} may be outdated. Recommend 11.0+")
        except Exception as e:
            raise RuntimeError(f"ExifTool not found or invalid: {e}")

    def __enter__(self):
        """Start ExifTool in stay_open mode."""
        self.et = exiftool.ExifTool(executable_=self.exiftool_path)
        self.et.start()
        logger.info("ExifTool started in stay_open mode")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop ExifTool process."""
        if self.et:
            self.et.terminate()
            logger.info("ExifTool terminated")

    def write_xmp_sidecar(
        self,
        image_path: Path,
        tags: List[str],
        description: Optional[str] = None,
        rating: Optional[int] = None,
        source_url: Optional[str] = None
    ) -> bool:
        """Write metadata to XMP sidecar.

        Args:
            image_path: Path to image file
            tags: List of tags to write
            description: Optional description text
            rating: Optional rating (0-5)
            source_url: Optional source URL

        Returns:
            True if successful, False otherwise
        """
        try:
            sidecar_path = Path(str(image_path) + '.xmp')

            # Build ExifTool parameters
            params = [
                '-o', str(sidecar_path),  # Output to sidecar
                '-overwrite_original',    # No backup files
            ]

            # Write tags to multiple fields for compatibility
            for tag in tags:
                # Escape special characters
                safe_tag = self._sanitize_tag(tag)
                params.extend([
                    f'-XMP-digiKam:TagsList={safe_tag}',
                    f'-IPTC:Keywords={safe_tag}',
                    f'-XMP-dc:Subject={safe_tag}',
                ])

            # Optional fields
            if description:
                params.append(f'-XMP-dc:Description={description}')

            if rating is not None and 0 <= rating <= 5:
                params.append(f'-XMP-xmp:Rating={rating}')

            if source_url:
                params.append(f'-XMP-dc:Source={source_url}')

            # Add image path as final parameter
            params.append(str(image_path))

            # Execute ExifTool
            result = self.et.execute(*params)

            # Verify sidecar was created
            if not sidecar_path.exists():
                logger.error(f"XMP sidecar not created: {sidecar_path}")
                return False

            # Validate XMP is well-formed
            if not self._validate_xmp(sidecar_path):
                logger.warning(f"XMP validation failed: {sidecar_path}")
                # Don't fail - Immich may still read it

            logger.debug(f"Created XMP sidecar: {sidecar_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write XMP for {image_path}: {e}")
            return False

    def write_xmp_batch(
        self,
        image_metadata: List[Dict]
    ) -> Dict[str, int]:
        """Write XMP sidecars for multiple images.

        Args:
            image_metadata: List of dicts with keys:
                - image_path: Path object
                - tags: List[str]
                - description: Optional[str]
                - rating: Optional[int]
                - source_url: Optional[str]

        Returns:
            Dict with 'success', 'failed', 'total' counts
        """
        total = len(image_metadata)
        success = 0
        failed = 0

        logger.info(f"Writing XMP sidecars for {total} images...")

        for idx, metadata in enumerate(image_metadata, 1):
            image_path = metadata['image_path']

            if self.write_xmp_sidecar(
                image_path=image_path,
                tags=metadata.get('tags', []),
                description=metadata.get('description'),
                rating=metadata.get('rating'),
                source_url=metadata.get('source_url')
            ):
                success += 1
            else:
                failed += 1

            # Progress logging every 100 images
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")

        logger.info(f"XMP batch complete: {success} success, {failed} failed")

        return {
            'success': success,
            'failed': failed,
            'total': total
        }

    @staticmethod
    def _sanitize_tag(tag: str) -> str:
        """Sanitize tag for XMP format.

        Removes or escapes characters that may cause issues:
        - Control characters
        - Leading/trailing whitespace
        - Multiple consecutive spaces
        """
        # Remove control characters
        tag = ''.join(char for char in tag if ord(char) >= 32)

        # Trim and normalize spaces
        tag = ' '.join(tag.split())

        # Escape XML special characters
        tag = tag.replace('&', '&amp;')
        tag = tag.replace('<', '&lt;')
        tag = tag.replace('>', '&gt;')
        tag = tag.replace('"', '&quot;')
        tag = tag.replace("'", '&apos;')

        return tag

    @staticmethod
    def _validate_xmp(xmp_path: Path) -> bool:
        """Validate XMP file is well-formed XML.

        Args:
            xmp_path: Path to XMP file

        Returns:
            True if valid XML, False otherwise
        """
        try:
            ET.parse(xmp_path)
            return True
        except ET.ParseError as e:
            logger.warning(f"XMP parse error in {xmp_path}: {e}")
            return False
```

### Metadata Builder

```python
# src/xmp_writer/metadata_builder.py
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MetadataBuilder:
    """Build metadata structures for XMP writing."""

    @staticmethod
    def build_from_booru_tags(
        image_path: Path,
        booru_result: Dict,
        include_rating: bool = False
    ) -> Dict:
        """Build metadata dict from booru search results.

        Args:
            image_path: Path to image file
            booru_result: Result from BooruTagger
            include_rating: Whether to include rating in metadata

        Returns:
            Dict suitable for ExifToolWrapper.write_xmp_sidecar()
        """
        metadata = {
            'image_path': image_path,
            'tags': [],
            'description': None,
            'rating': None,
            'source_url': None
        }

        # Extract tags from booru result
        if 'tags' in booru_result:
            # Combine different tag types
            all_tags = []

            # General tags
            all_tags.extend(booru_result['tags'].get('general', []))

            # Character tags
            for char in booru_result['tags'].get('characters', []):
                if isinstance(char, dict):
                    char_tag = char['name']
                    if char.get('series'):
                        char_tag = f"{char['series']}/{char['name']}"
                    all_tags.append(char_tag)
                else:
                    all_tags.append(str(char))

            # Series tags
            series = booru_result['tags'].get('series', [])
            all_tags.extend([f"Series/{s}" for s in series])

            # Artist tags
            artists = booru_result['tags'].get('artists', [])
            all_tags.extend([f"Artist/{a}" for a in artists])

            metadata['tags'] = all_tags

        # Description from similarity and source
        if booru_result.get('similarity'):
            similarity = booru_result['similarity']
            source = booru_result.get('site', 'unknown')
            metadata['description'] = f"Matched via {source} ({similarity:.1f}% similarity)"

        # Source URL
        if 'url' in booru_result:
            metadata['source_url'] = booru_result['url']

        # Rating (convert booru rating to 1-5 scale)
        if include_rating and 'rating' in booru_result.get('tags', {}):
            rating_map = {
                'safe': 5,
                'questionable': 3,
                'explicit': 1,
                'sensitive': 3
            }
            booru_rating = booru_result['tags']['rating']
            metadata['rating'] = rating_map.get(booru_rating)

        return metadata

    @staticmethod
    def build_from_content_analysis(
        image_path: Path,
        content_result: Dict
    ) -> Dict:
        """Build metadata dict from content analysis results.

        Args:
            image_path: Path to image file
            content_result: Result from ContentAnalyzer

        Returns:
            Dict suitable for ExifToolWrapper.write_xmp_sidecar()
        """
        metadata = {
            'image_path': image_path,
            'tags': [],
            'description': None,
            'rating': None,
            'source_url': None
        }

        # Add classification tags
        if 'style' in content_result:
            style = content_result['style']
            confidence = content_result.get('style_confidence', 0)
            if confidence > 0.6:
                metadata['tags'].append(f"Style/{style}")

        # Add object detection tags
        if 'objects' in content_result:
            for obj in content_result['objects']:
                if obj.get('confidence', 0) > 0.7:
                    metadata['tags'].append(f"Contains/{obj['class']}")

        # Description
        metadata['description'] = "Analyzed by AI content classifier"

        return metadata

    @staticmethod
    def merge_metadata(
        base_metadata: Dict,
        additional_metadata: Dict
    ) -> Dict:
        """Merge two metadata dicts, combining tags.

        Args:
            base_metadata: Base metadata dict
            additional_metadata: Additional metadata to merge

        Returns:
            Merged metadata dict
        """
        merged = base_metadata.copy()

        # Combine tags (deduplicate)
        all_tags = set(base_metadata.get('tags', []))
        all_tags.update(additional_metadata.get('tags', []))
        merged['tags'] = sorted(all_tags)

        # Prefer non-None values for other fields
        for key in ['description', 'rating', 'source_url']:
            if not merged.get(key) and additional_metadata.get(key):
                merged[key] = additional_metadata[key]

        return merged
```

### Usage Example

```python
# Example: Write XMP sidecars after booru tagging
from pathlib import Path
from src.xmp_writer.exiftool_wrapper import ExifToolWrapper
from src.xmp_writer.metadata_builder import MetadataBuilder

# Prepare metadata for batch
image_metadata = []
for image_path, booru_result in tagged_images:
    metadata = MetadataBuilder.build_from_booru_tags(
        image_path=image_path,
        booru_result=booru_result,
        include_rating=True
    )
    image_metadata.append(metadata)

# Write all XMP sidecars in batch
with ExifToolWrapper() as et:
    results = et.write_xmp_batch(image_metadata)
    print(f"Success: {results['success']}, Failed: {results['failed']}")
```

## Testing Strategy

### Unit Tests

```python
# tests/test_xmp_writer/test_exiftool_wrapper.py
import pytest
from pathlib import Path

def test_sanitize_tag():
    assert ExifToolWrapper._sanitize_tag("  blue eyes  ") == "blue eyes"
    assert ExifToolWrapper._sanitize_tag("tag&test") == "tag&amp;test"
    assert ExifToolWrapper._sanitize_tag("tag<>test") == "tag&lt;&gt;test"

def test_validate_xmp(tmp_path):
    # Create valid XMP
    xmp_path = tmp_path / "test.xmp"
    xmp_path.write_text('<?xml version="1.0"?><root><tag>value</tag></root>')
    assert ExifToolWrapper._validate_xmp(xmp_path) == True

    # Create invalid XMP
    invalid_xmp = tmp_path / "invalid.xmp"
    invalid_xmp.write_text('<root><unclosed>')
    assert ExifToolWrapper._validate_xmp(invalid_xmp) == False

def test_metadata_builder_from_booru():
    booru_result = {
        'status': 'success',
        'similarity': 85.5,
        'site': 'Danbooru',
        'url': 'https://danbooru.donmai.us/posts/12345',
        'tags': {
            'general': ['blue eyes', 'long hair'],
            'characters': [{'name': 'Hinata Hyuga', 'series': 'Naruto'}],
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

    assert 'blue eyes' in metadata['tags']
    assert 'Naruto/Hinata Hyuga' in metadata['tags']
    assert metadata['rating'] == 5
    assert 'Danbooru' in metadata['description']
```

### Integration Tests

```python
# tests/test_xmp_writer/test_integration.py
def test_write_xmp_sidecar_integration(tmp_path, sample_image):
    """Test actual XMP writing with ExifTool."""
    # Copy sample image to tmp
    image_path = tmp_path / "test.jpg"
    shutil.copy(sample_image, image_path)

    # Write XMP
    with ExifToolWrapper() as et:
        success = et.write_xmp_sidecar(
            image_path=image_path,
            tags=['test tag', 'anime', 'blue eyes'],
            description='Test description',
            rating=4
        )

    assert success == True

    # Verify XMP file exists
    xmp_path = Path(str(image_path) + '.xmp')
    assert xmp_path.exists()

    # Read back with ExifTool to verify
    with exiftool.ExifTool() as et:
        metadata = et.get_metadata(str(image_path))
        # Check that XMP was read
        assert 'XMP:TagsList' in metadata or 'IPTC:Keywords' in metadata
```

### Performance Tests

```python
def test_batch_performance(tmp_path, generate_sample_images):
    """Verify batch writing meets performance target."""
    # Generate 100 sample images
    images = generate_sample_images(tmp_path, count=100)

    metadata_list = [
        {
            'image_path': img,
            'tags': ['tag1', 'tag2', 'tag3'],
            'description': 'Test'
        }
        for img in images
    ]

    import time
    start = time.time()

    with ExifToolWrapper() as et:
        results = et.write_xmp_batch(metadata_list)

    elapsed = time.time() - start

    assert results['success'] == 100
    assert elapsed < 10  # 100 images in under 10 seconds
    print(f"Processed 100 images in {elapsed:.2f} seconds")
```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests pass with 85%+ coverage
- [ ] Integration test writes and validates XMP
- [ ] Performance test: 1,000 images in <60 seconds
- [ ] Verified Immich reads generated XMP files
- [ ] Error handling for missing ExifTool
- [ ] Logging implemented for all operations
- [ ] Configuration options documented
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-001 (Project setup for configuration)

**Blocks:**
- STORY-008 (Workflow orchestration needs XMP writer)

## Notes

- ExifTool must be downloaded separately from https://exiftool.org/
- stay_open mode provides 60x performance improvement
- Immich prioritizes `XMP-digiKam:TagsList` field
- XMP sidecars should use `.jpg.xmp` format (not `.xmp` only)
- Consider batch size tuning for optimal performance

## Risks

- **Low Risk:** ExifTool not in PATH on user's system
  - *Mitigation:* Clear setup instructions, auto-download option

- **Low Risk:** Generated XMP format incompatible with Immich
  - *Mitigation:* Test with real Immich instance early

## Related Files

- `/src/xmp_writer/exiftool_wrapper.py`
- `/src/xmp_writer/metadata_builder.py`
- `/tests/test_xmp_writer/`
- `/config/config.yaml` (exiftool_path setting)

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
