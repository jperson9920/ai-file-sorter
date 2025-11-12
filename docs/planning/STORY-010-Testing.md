# STORY-010: End-to-End Testing and Validation

**Epic:** EPIC-001
**Story Points:** 5
**Priority:** P1 - High
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 3-4 days

## User Story

As a **developer**, I want to **comprehensively test the entire system end-to-end** so that **I can ensure all components work together correctly and meet the performance and quality targets**.

## Acceptance Criteria

### AC1: Unit Test Coverage
- [ ] Achieve 85%+ code coverage across all modules
- [ ] Unit tests for all booru clients
- [ ] Unit tests for XMP writer and metadata builder
- [ ] Unit tests for content analysis components
- [ ] Unit tests for preference learning
- [ ] Unit tests for workflow orchestration
- [ ] All tests pass on Windows 11

### AC2: Integration Tests
- [ ] Test complete workflow with 100 sample images
- [ ] Test reverse image search with real APIs
- [ ] Test XMP writing and reading back with ExifTool
- [ ] Test content analysis with various image types
- [ ] Test NAS sync (local directory simulation)
- [ ] Test preference learning over multiple runs

### AC3: Performance Tests
- [ ] Reverse search: 200 images without rate limiting
- [ ] XMP writing: 1,000 images in <60 seconds
- [ ] Content analysis: 1,000 images in <5 minutes
- [ ] Complete workflow: 1,000 images in <60 minutes
- [ ] NAS sync: 1GB of data in <30 seconds (gigabit ethernet)

### AC4: Error Handling Tests
- [ ] Test graceful handling of API failures
- [ ] Test recovery from network interruptions
- [ ] Test handling of corrupted images
- [ ] Test handling of invalid JSON files
- [ ] Test handling of disk full scenarios
- [ ] Verify error logging is comprehensive

### AC5: Compatibility Tests
- [ ] Test on Windows 11 (primary target)
- [ ] Test with various image formats (JPG, PNG, WebP)
- [ ] Test with Immich (verify XMP reading)
- [ ] Test with different Python versions (3.9, 3.10, 3.11, 3.12)
- [ ] Test with and without GPU

### AC6: Regression Tests
- [ ] Create regression test suite with 50 sample images
- [ ] Document expected outputs for each sample
- [ ] Automate regression testing
- [ ] Run regression tests before each release

## Technical Implementation

### Test Fixtures and Utilities

```python
# tests/conftest.py
import pytest
from pathlib import Path
import shutil
from PIL import Image
import json

@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace with directory structure."""
    workspace = {
        'inbox': tmp_path / 'inbox',
        'sorted': tmp_path / 'sorted',
        'working': tmp_path / 'working',
        'data': tmp_path / 'data',
        'logs': tmp_path / 'logs'
    }

    for path in workspace.values():
        path.mkdir(parents=True)

    return workspace

@pytest.fixture
def sample_anime_image(tmp_path):
    """Create a sample anime-style image for testing."""
    image_path = tmp_path / "anime_sample.jpg"

    # Create a simple colored image
    img = Image.new('RGB', (512, 512), color=(100, 150, 200))
    img.save(image_path, 'JPEG')

    return image_path

@pytest.fixture
def sample_images(tmp_path, count=10):
    """Create multiple sample images."""
    images = []
    for i in range(count):
        image_path = tmp_path / f"sample_{i:03d}.jpg"
        img = Image.new('RGB', (256, 256), color=(i*20, 100, 200))
        img.save(image_path, 'JPEG')
        images.append(image_path)

    return images

@pytest.fixture
def mock_booru_response():
    """Mock booru API response."""
    return {
        'status': 'success',
        'similarity': 85.5,
        'site': 'Danbooru',
        'url': 'https://danbooru.donmai.us/posts/12345',
        'tags': {
            'general': ['blue_eyes', 'long_hair', 'school_uniform'],
            'characters': [{'name': 'Hinata Hyuga', 'series': 'Naruto'}],
            'series': ['Naruto'],
            'artists': ['Artist Name'],
            'rating': 'safe'
        }
    }

@pytest.fixture
def test_config(tmp_workspace):
    """Create test configuration."""
    return {
        'directories': {
            'inbox': str(tmp_workspace['inbox']),
            'sorted': str(tmp_workspace['sorted']),
            'working': str(tmp_workspace['working']),
            'nas_path': ''
        },
        'api': {
            'saucenao': {
                'api_key': 'test_key',
                'rate_limit': 6,
                'min_similarity': 70.0
            },
            'danbooru': {
                'username': 'test_user',
                'api_key': 'test_key'
            },
            'iqdb': {
                'enabled': True,
                'min_similarity': 80.0
            }
        },
        'content_analysis': {
            'enabled': True,
            'models': {
                'clip': {
                    'model_name': 'openai/clip-vit-base-patch32',
                    'cache_dir': str(tmp_workspace['data'] / 'models')
                },
                'faster_rcnn': {
                    'model_name': 'fasterrcnn_resnet50_fpn',
                    'confidence_threshold': 0.7
                }
            },
            'classifications': [
                {'label': 'anime style illustration', 'threshold': 0.6},
                {'label': 'realistic photograph', 'threshold': 0.6}
            ]
        },
        'xmp': {
            'exiftool_path': '',
            'sidecar_format': '{filename}.xmp',
            'fields': ['XMP-digiKam:TagsList', 'IPTC:Keywords'],
            'include_rating': True,
            'include_description': True
        },
        'workflow': {
            'batch_size': 10,
            'parallel_workers': 2,
            'enable_gui_review': False,
            'auto_approve_high_confidence': True
        },
        'sync': {
            'enabled': False
        },
        'learning': {
            'database_path': str(tmp_workspace['data'] / 'preferences.db'),
            'min_confidence': 0.7,
            'min_samples': 50
        },
        'logging': {
            'level': 'DEBUG',
            'file': str(tmp_workspace['logs'] / 'test.log'),
            'console_output': False
        },
        'performance': {
            'cache_enabled': True,
            'cache_ttl_hours': 48,
            'max_cache_size_mb': 100
        }
    }
```

### End-to-End Test Suite

```python
# tests/test_e2e/test_complete_workflow.py
import pytest
from pathlib import Path
import shutil
from src.workflow.orchestrator import WorkflowOrchestrator
from src.xmp_writer.exiftool_wrapper import ExifToolWrapper

@pytest.mark.e2e
class TestCompleteWorkflow:
    """End-to-end tests for complete workflow."""

    def test_workflow_with_sample_images(
        self,
        test_config,
        tmp_workspace,
        sample_images
    ):
        """Test complete workflow with sample images."""
        # Copy sample images to inbox
        for img in sample_images:
            shutil.copy(img, tmp_workspace['inbox'])

        # Run workflow
        orchestrator = WorkflowOrchestrator(test_config)
        results = orchestrator.process_inbox(auto_approve=True, skip_existing=False)

        # Verify results
        assert results['total_images'] == len(sample_images)
        assert results['processed'] > 0

        # Verify files moved to sorted directory
        sorted_files = list(tmp_workspace['sorted'].rglob('*.jpg'))
        assert len(sorted_files) > 0

        # Verify XMP sidecars created
        xmp_files = list(tmp_workspace['sorted'].rglob('*.xmp'))
        assert len(xmp_files) > 0

    def test_xmp_readable_by_immich(self, sample_anime_image, tmp_path):
        """Test that generated XMP files are readable by ExifTool (Immich uses ExifTool)."""
        tags = ['anime', 'character', 'blue_eyes']

        with ExifToolWrapper() as et:
            # Write XMP
            success = et.write_xmp_sidecar(
                image_path=sample_anime_image,
                tags=tags,
                description='Test image',
                rating=4
            )

            assert success == True

            # Read back with ExifTool
            xmp_path = Path(str(sample_anime_image) + '.xmp')
            assert xmp_path.exists()

            # Verify content
            import exiftool
            with exiftool.ExifTool() as reader:
                metadata = reader.get_metadata(str(sample_anime_image))

                # Check tags are present
                # Note: Field names may vary, check multiple possibilities
                tag_fields = ['XMP:TagsList', 'IPTC:Keywords', 'XMP:Subject']
                found_tags = False

                for field in tag_fields:
                    if field in metadata:
                        found_tags = True
                        break

                assert found_tags, "Tags not found in XMP metadata"

    @pytest.mark.slow
    def test_performance_target(self, test_config, tmp_workspace):
        """Test that workflow meets performance targets."""
        import time
        from PIL import Image

        # Generate 100 test images
        test_images = []
        for i in range(100):
            img_path = tmp_workspace['inbox'] / f"test_{i:04d}.jpg"
            img = Image.new('RGB', (512, 512), color=(i*2, 100, 150))
            img.save(img_path, 'JPEG')
            test_images.append(img_path)

        # Run workflow
        orchestrator = WorkflowOrchestrator(test_config)

        start = time.time()
        results = orchestrator.process_inbox(auto_approve=True)
        elapsed = time.time() - start

        # Performance targets (relaxed for testing)
        # Real target: 1000 images in 60 minutes = 100 images in 6 minutes
        assert elapsed < 360, f"Workflow too slow: {elapsed:.1f}s for 100 images"

        print(f"Processed 100 images in {elapsed:.1f}s ({100/elapsed:.1f} images/min)")

    def test_preference_learning_cycle(self, test_config, tmp_workspace, sample_images):
        """Test that preference learning improves suggestions."""
        orchestrator = WorkflowOrchestrator(test_config)

        # First pass: everything goes to Uncategorized
        shutil.copytree(sample_images[0].parent, tmp_workspace['inbox'], dirs_exist_ok=True)

        results1 = orchestrator.process_inbox(auto_approve=True)

        # Manually correct categorization (simulate user corrections)
        for img in tmp_workspace['sorted'].rglob('*.jpg'):
            # Move to Anime/Characters folder
            dest_dir = tmp_workspace['sorted'] / 'Anime' / 'Characters'
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Record as correction
            orchestrator.preference_tracker.record_movement(
                file_path=img,
                suggested_category='Uncategorized',
                actual_category='Anime/Characters',
                content_analysis={'style': 'anime style illustration', 'style_confidence': 0.9, 'persons_detected': 1}
            )

        # Second pass: should learn from corrections
        # Generate new similar images
        for i in range(10):
            img_path = tmp_workspace['inbox'] / f"new_{i:04d}.jpg"
            img = Image.new('RGB', (512, 512), color=(100, 150, 200))
            img.save(img_path, 'JPEG')

        results2 = orchestrator.process_inbox(auto_approve=True)

        # Check preference statistics
        stats = orchestrator.preference_tracker.get_statistics()
        assert stats['learned_patterns'] > 0, "No patterns learned"

    def test_error_recovery(self, test_config, tmp_workspace):
        """Test graceful error handling."""
        # Create corrupted image
        corrupted = tmp_workspace['inbox'] / 'corrupted.jpg'
        corrupted.write_bytes(b'not a valid image')

        # Create valid image
        valid = tmp_workspace['inbox'] / 'valid.jpg'
        img = Image.new('RGB', (256, 256), color='blue')
        img.save(valid, 'JPEG')

        # Run workflow
        orchestrator = WorkflowOrchestrator(test_config)
        results = orchestrator.process_inbox(auto_approve=True)

        # Should process valid image despite corrupted one
        assert results['processed'] >= 1
        assert results['failed'] >= 1

    def test_resume_from_interruption(self, test_config, tmp_workspace, sample_images):
        """Test resuming workflow after interruption."""
        # Copy sample images
        for img in sample_images:
            shutil.copy(img, tmp_workspace['inbox'])

        # Process first half
        orchestrator = WorkflowOrchestrator(test_config)

        # Simulate partial processing
        # Process and move first 5 images manually
        for img in list(tmp_workspace['inbox'].glob('*.jpg'))[:5]:
            # Create XMP to mark as processed
            xmp_path = Path(str(img) + '.xmp')
            xmp_path.write_text('<?xml version="1.0"?><x:xmpmeta></x:xmpmeta>')

        # Resume workflow (should skip existing XMP files)
        results = orchestrator.process_inbox(auto_approve=True, skip_existing=True)

        # Should only process remaining images
        assert results['skipped'] == 5
        assert results['total_images'] == 5  # Remaining images
```

### Performance Benchmark Suite

```python
# tests/test_performance/test_benchmarks.py
import pytest
import time
from pathlib import Path
from PIL import Image

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_xmp_batch_writing_performance(self, tmp_path):
        """Benchmark XMP batch writing."""
        from src.xmp_writer.exiftool_wrapper import ExifToolWrapper

        # Generate 1000 test images
        images = []
        for i in range(1000):
            img_path = tmp_path / f"img_{i:04d}.jpg"
            img = Image.new('RGB', (256, 256), color='blue')
            img.save(img_path, 'JPEG')
            images.append(img_path)

        # Prepare metadata
        image_metadata = [
            {
                'image_path': img,
                'tags': ['tag1', 'tag2', 'tag3'],
                'description': 'Test'
            }
            for img in images
        ]

        # Benchmark
        start = time.time()

        with ExifToolWrapper() as et:
            results = et.write_xmp_batch(image_metadata)

        elapsed = time.time() - start

        # Target: <60 seconds for 1000 images
        assert elapsed < 60, f"XMP writing too slow: {elapsed:.1f}s"
        assert results['success'] == 1000

        print(f"XMP batch write: 1000 images in {elapsed:.1f}s ({1000/elapsed:.1f} img/s)")

    @pytest.mark.slow
    def test_content_analysis_performance(self, tmp_path, test_config):
        """Benchmark content analysis."""
        from src.content_analysis.content_analyzer import ContentAnalyzer

        # Generate 100 test images (scaled down for testing)
        images = []
        for i in range(100):
            img_path = tmp_path / f"img_{i:04d}.jpg"
            img = Image.new('RGB', (512, 512), color=(i*2, 100, 150))
            img.save(img_path, 'JPEG')
            images.append(img_path)

        # Benchmark
        analyzer = ContentAnalyzer(test_config['content_analysis'])

        start = time.time()
        results = analyzer.analyze_batch(images)
        elapsed = time.time() - start

        # Target: 1000 images in 5 minutes = 100 images in 30 seconds
        assert elapsed < 30, f"Content analysis too slow: {elapsed:.1f}s"

        print(f"Content analysis: 100 images in {elapsed:.1f}s ({100/elapsed:.1f} img/s)")
        print(f"Extrapolated: 1000 images in ~{elapsed*10:.1f}s")
```

## Testing Strategy

### Test Organization
```
tests/
├── conftest.py              # Shared fixtures
├── test_booru/              # Booru client tests
├── test_xmp_writer/         # XMP writer tests
├── test_content_analysis/   # Content analysis tests
├── test_learning/           # Preference learning tests
├── test_workflow/           # Workflow orchestration tests
├── test_utils/              # Utility tests
├── test_e2e/               # End-to-end integration tests
├── test_performance/        # Performance benchmarks
└── test_regression/         # Regression tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest -m "not e2e and not slow and not benchmark"

# Run integration tests
pytest -m e2e

# Run performance benchmarks
pytest -m benchmark

# Run specific test file
pytest tests/test_workflow/test_orchestrator.py

# Run with verbose output
pytest -v -s
```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] 85%+ code coverage achieved
- [ ] All unit tests pass
- [ ] Integration tests with 100 images succeed
- [ ] Performance benchmarks meet targets
- [ ] Error handling tests pass
- [ ] Regression test suite created
- [ ] CI/CD pipeline configured (optional)
- [ ] Test documentation complete

## Dependencies

**Depends On:**
- All implementation stories (STORY-002 through STORY-009)

**Blocks:**
- STORY-011 (Documentation - needs working system)

## Notes

- Use pytest markers to categorize tests (@pytest.mark.slow, @pytest.mark.e2e, etc.)
- Mock external APIs in unit tests to avoid rate limits
- Use real APIs in integration tests (requires API keys)
- Consider using pytest-xdist for parallel test execution

## Risks

- **Medium Risk:** Performance tests may fail on slower hardware
  - *Mitigation:* Adjust targets based on hardware capabilities

- **Low Risk:** Integration tests may fail due to API changes
  - *Mitigation:* Mock external dependencies, version pin packages

## Related Files

- `/tests/conftest.py`
- `/tests/test_e2e/`
- `/tests/test_performance/`
- `/pytest.ini`
- `/.github/workflows/tests.yml` (CI/CD)

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
