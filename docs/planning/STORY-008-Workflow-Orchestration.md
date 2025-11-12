# STORY-008: Integrated Workflow Orchestration and Batch Processing

**Epic:** EPIC-001
**Story Points:** 8
**Priority:** P0 - Critical
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 4-5 days

## User Story

As a **user**, I want to **run a complete automated workflow that processes images from inbox to NAS** so that **I can tag, categorize, and sync thousands of images with minimal manual intervention**.

## Acceptance Criteria

### AC1: Workflow Pipeline
- [ ] Implement complete 7-stage pipeline:
  1. Scan inbox for new images
  2. Reverse image search (SauceNAO/IQDB)
  3. Tag review and approval (optional GUI or auto-approve)
  4. XMP sidecar writing
  5. AI content analysis
  6. File categorization with learned preferences
  7. NAS sync
- [ ] Each stage can be enabled/disabled via configuration
- [ ] Pipeline supports partial execution (start from specific stage)

### AC2: Batch Processing
- [ ] Process images in configurable batch sizes (default: 100)
- [ ] Support processing entire inbox directory recursively
- [ ] Handle multiple image formats (JPG, PNG, WebP, etc.)
- [ ] Skip already-processed images (check for existing XMP)
- [ ] Resume interrupted processing

### AC3: Tag Review Interface
- [ ] CLI-based review interface for tag approval
- [ ] Display image thumbnail (if terminal supports)
- [ ] Show suggested tags with confidence scores
- [ ] Allow user to approve/edit/reject tags
- [ ] Support bulk operations (approve all, skip all)
- [ ] Optional auto-approve mode for high-confidence tags

### AC4: Progress Reporting
- [ ] Real-time progress bars for each stage
- [ ] Overall progress (images processed / total)
- [ ] Stage-specific metrics (API calls, cache hits, etc.)
- [ ] Estimated time remaining
- [ ] Performance statistics (images/minute, MB/s)

### AC5: Error Handling & Recovery
- [ ] Graceful handling of API failures (continue with next image)
- [ ] Retry logic for transient network errors
- [ ] Log all errors with detailed context
- [ ] Generate error report at end of processing
- [ ] Support resuming from checkpoint

### AC6: Output Organization
- [ ] Organize processed images into category folders
- [ ] Option to copy or move files (preserve originals)
- [ ] XMP sidecars stay alongside images
- [ ] Generate processing manifest (JSON log of all operations)

## Technical Implementation

### WorkflowOrchestrator Class

```python
# src/workflow/orchestrator.py
from pathlib import Path
from typing import List, Dict, Optional, Callable
import logging
from datetime import datetime
import json
from tqdm import tqdm

from src.booru.saucenao_client import SauceNAOClient
from src.booru.danbooru_client import DanbooruClient
from src.booru.iqdb_client import IQDBClient
from src.booru.tag_normalizer import TagNormalizer
from src.booru.cache_manager import CacheManager
from src.xmp_writer.exiftool_wrapper import ExifToolWrapper
from src.xmp_writer.metadata_builder import MetadataBuilder
from src.content_analysis.content_analyzer import ContentAnalyzer
from src.learning.preference_tracker import PreferenceTracker
from src.workflow.nas_sync import RobocopySync

logger = logging.getLogger(__name__)

class WorkflowOrchestrator:
    """Orchestrates the complete image tagging and categorization workflow."""

    def __init__(self, config: Dict):
        """Initialize workflow orchestrator.

        Args:
            config: Complete configuration dict
        """
        self.config = config
        self.inbox_dir = Path(config['directories']['inbox'])
        self.sorted_dir = Path(config['directories']['sorted'])
        self.working_dir = Path(config['directories']['working'])

        # Initialize components
        self._init_components()

        # Processing statistics
        self.stats = {
            'total_images': 0,
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'tags_found': 0,
            'tags_approved': 0,
            'content_analyzed': 0,
            'synced_to_nas': 0,
            'start_time': None,
            'end_time': None
        }

    def _init_components(self):
        """Initialize all workflow components."""
        # Cache manager
        cache_db = Path('data/cache/search_cache.db')
        self.cache_manager = CacheManager(
            db_path=str(cache_db),
            ttl_hours=self.config.get('performance', {}).get('cache_ttl_hours', 48)
        )

        # Reverse search clients
        self.saucenao = SauceNAOClient(
            api_key=self.config['api']['saucenao']['api_key'],
            cache_manager=self.cache_manager
        )

        self.danbooru = DanbooruClient(
            username=self.config['api']['danbooru']['username'],
            api_key=self.config['api']['danbooru']['api_key']
        )

        self.iqdb = IQDBClient()

        # Tag normalizer
        self.tag_normalizer = TagNormalizer()

        # Content analyzer
        if self.config['content_analysis']['enabled']:
            self.content_analyzer = ContentAnalyzer(self.config['content_analysis'])
        else:
            self.content_analyzer = None

        # Preference tracker
        self.preference_tracker = PreferenceTracker(
            db_path=self.config['learning']['database_path']
        )

        # NAS sync
        if self.config['sync']['enabled']:
            self.nas_sync = RobocopySync({
                'source_dir': str(self.sorted_dir),
                'dest_dir': self.config['directories']['nas_path'],
                'robocopy_options': self.config['sync']['robocopy_options'],
                'exclude_files': [],
                'exclude_dirs': []
            })
        else:
            self.nas_sync = None

    def process_inbox(
        self,
        auto_approve: bool = False,
        skip_existing: bool = True
    ) -> Dict:
        """Process all images in inbox directory.

        Args:
            auto_approve: Automatically approve all tags
            skip_existing: Skip images that already have XMP sidecars

        Returns:
            Dict with processing statistics
        """
        logger.info(f"Starting workflow: processing inbox {self.inbox_dir}")
        self.stats['start_time'] = datetime.now()

        # Find all images
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
        all_images = []
        for ext in image_extensions:
            all_images.extend(self.inbox_dir.rglob(ext))

        # Filter out already processed
        if skip_existing:
            images_to_process = [
                img for img in all_images
                if not Path(str(img) + '.xmp').exists()
            ]
            self.stats['skipped'] = len(all_images) - len(images_to_process)
        else:
            images_to_process = all_images

        self.stats['total_images'] = len(images_to_process)

        if self.stats['total_images'] == 0:
            logger.info("No new images to process")
            return self.stats

        logger.info(f"Processing {self.stats['total_images']} images...")

        # Process in batches
        batch_size = self.config['workflow']['batch_size']

        with ExifToolWrapper() as exiftool:
            for i in range(0, len(images_to_process), batch_size):
                batch = images_to_process[i:i+batch_size]
                self._process_batch(batch, exiftool, auto_approve)

        # Sync to NAS if enabled
        if self.nas_sync:
            logger.info("Syncing to NAS...")
            sync_result = self.nas_sync.sync()
            if sync_result['status'] == 'success':
                self.stats['synced_to_nas'] = sync_result.get('files_copied', 0)

        # Generate final report
        self.stats['end_time'] = datetime.now()
        self._save_processing_manifest()
        self._print_final_report()

        return self.stats

    def _process_batch(
        self,
        images: List[Path],
        exiftool: ExifToolWrapper,
        auto_approve: bool
    ):
        """Process a batch of images through the pipeline.

        Args:
            images: List of image paths
            exiftool: ExifTool wrapper instance
            auto_approve: Auto-approve tags
        """
        logger.info(f"Processing batch of {len(images)} images")

        for image_path in tqdm(images, desc="Processing"):
            try:
                result = self._process_single_image(
                    image_path,
                    exiftool,
                    auto_approve
                )

                if result['status'] == 'success':
                    self.stats['processed'] += 1
                else:
                    self.stats['failed'] += 1

            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                self.stats['failed'] += 1

    def _process_single_image(
        self,
        image_path: Path,
        exiftool: ExifToolWrapper,
        auto_approve: bool
    ) -> Dict:
        """Process a single image through complete pipeline.

        Args:
            image_path: Path to image
            exiftool: ExifTool wrapper
            auto_approve: Auto-approve tags

        Returns:
            Result dict with status and details
        """
        result = {
            'image_path': str(image_path),
            'status': 'pending',
            'stages': {}
        }

        # Stage 1: Reverse image search
        logger.debug(f"Stage 1: Reverse search for {image_path.name}")
        search_result = self._run_reverse_search(image_path)
        result['stages']['reverse_search'] = search_result

        # Extract tags if match found
        tags = []
        booru_result = None

        if search_result['status'] == 'success':
            self.stats['tags_found'] += 1

            # Stage 2: Extract tags from Danbooru
            if search_result.get('url'):
                booru_result = self._extract_tags(search_result['url'])
                if booru_result:
                    tags = self._flatten_tags(booru_result)

        # Stage 3: Tag review (if enabled and not auto-approve)
        if tags and not auto_approve and self.config['workflow']['enable_gui_review']:
            approved_tags = self._review_tags(image_path, tags, booru_result)
            if approved_tags:
                tags = approved_tags
                self.stats['tags_approved'] += 1
        elif tags:
            self.stats['tags_approved'] += 1

        # Stage 4: Content analysis
        content_result = None
        if self.content_analyzer:
            logger.debug(f"Stage 4: Content analysis for {image_path.name}")
            content_result = self.content_analyzer.analyze_image(image_path)
            if content_result['status'] == 'success':
                self.stats['content_analyzed'] += 1
                result['stages']['content_analysis'] = content_result

        # Stage 5: Category suggestion with preference learning
        logger.debug(f"Stage 5: Category suggestion for {image_path.name}")
        if content_result:
            suggested_category = self.content_analyzer.get_category_suggestion(content_result)

            # Apply learned preferences
            learned_category, confidence = self.preference_tracker.suggest_category(
                content_analysis=content_result,
                tags=tags,
                default_category=suggested_category
            )

            if confidence >= 0.7:
                final_category = learned_category
            else:
                final_category = suggested_category

            result['stages']['categorization'] = {
                'suggested': suggested_category,
                'learned': learned_category,
                'confidence': confidence,
                'final': final_category
            }
        else:
            final_category = "Uncategorized"

        # Stage 6: Write XMP sidecar
        if tags:
            logger.debug(f"Stage 6: Writing XMP for {image_path.name}")
            metadata = MetadataBuilder.build_from_booru_tags(
                image_path=image_path,
                booru_result=search_result if booru_result else {'tags': {'general': tags}},
                include_rating=self.config['xmp']['include_rating']
            )

            # Merge content analysis tags
            if content_result:
                content_metadata = MetadataBuilder.build_from_content_analysis(
                    image_path=image_path,
                    content_result=content_result
                )
                metadata = MetadataBuilder.merge_metadata(metadata, content_metadata)

            xmp_success = exiftool.write_xmp_sidecar(
                image_path=image_path,
                tags=metadata['tags'],
                description=metadata.get('description'),
                rating=metadata.get('rating'),
                source_url=metadata.get('source_url')
            )

            result['stages']['xmp_write'] = {'success': xmp_success}

        # Stage 7: Move to category folder
        dest_dir = self.sorted_dir / final_category
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = dest_dir / image_path.name

        # Move or copy
        import shutil
        if self.config['workflow'].get('preserve_originals', False):
            shutil.copy2(image_path, dest_path)
            # Also copy XMP
            xmp_path = Path(str(image_path) + '.xmp')
            if xmp_path.exists():
                shutil.copy2(xmp_path, Path(str(dest_path) + '.xmp'))
        else:
            shutil.move(image_path, dest_path)
            # Also move XMP
            xmp_path = Path(str(image_path) + '.xmp')
            if xmp_path.exists():
                shutil.move(xmp_path, Path(str(dest_path) + '.xmp'))

        result['final_location'] = str(dest_path)

        # Record movement for preference learning
        self.preference_tracker.record_movement(
            file_path=dest_path,
            suggested_category=result['stages'].get('categorization', {}).get('suggested', 'Uncategorized'),
            actual_category=final_category,
            content_analysis=content_result,
            tags=tags
        )

        result['status'] = 'success'
        return result

    def _run_reverse_search(self, image_path: Path) -> Dict:
        """Run reverse image search with fallback.

        Args:
            image_path: Path to image

        Returns:
            Search result dict
        """
        # Try SauceNAO first
        result = asyncio.run(self.saucenao.search_image(
            image_path=image_path,
            min_similarity=self.config['api']['saucenao']['min_similarity']
        ))

        if result['status'] == 'success':
            return result

        # Fallback to IQDB
        if self.config['api']['iqdb']['enabled']:
            result = asyncio.run(self.iqdb.search_image(
                image_path=str(image_path),
                min_similarity=self.config['api']['iqdb']['min_similarity']
            ))

        return result

    def _extract_tags(self, url: str) -> Optional[Dict]:
        """Extract tags from booru URL.

        Args:
            url: Post URL

        Returns:
            Tag dict or None
        """
        post_id = self.danbooru.extract_post_id(url)
        if not post_id:
            return None

        try:
            tags = self.danbooru.get_tags(post_id, max_tags=10)
            normalized = self.tag_normalizer.normalize_post_tags(tags)
            return normalized
        except Exception as e:
            logger.error(f"Failed to extract tags: {e}")
            return None

    def _flatten_tags(self, booru_result: Dict) -> List[str]:
        """Flatten booru tag dict to simple list.

        Args:
            booru_result: Normalized tag dict

        Returns:
            List of tag strings
        """
        all_tags = []
        all_tags.extend(booru_result.get('general', []))

        for char in booru_result.get('characters', []):
            if char.get('series'):
                all_tags.append(f"{char['series']}/{char['name']}")
            else:
                all_tags.append(char['name'])

        all_tags.extend(booru_result.get('series', []))

        return all_tags

    def _review_tags(
        self,
        image_path: Path,
        tags: List[str],
        booru_result: Optional[Dict]
    ) -> Optional[List[str]]:
        """Present tags to user for review.

        Args:
            image_path: Path to image
            tags: Suggested tags
            booru_result: Full booru result

        Returns:
            Approved tags or None if rejected
        """
        print(f"\n{'='*60}")
        print(f"Image: {image_path.name}")
        print(f"{'='*60}")

        if booru_result:
            print(f"Source: {booru_result.get('source', 'Unknown')}")
            print(f"Similarity: {booru_result.get('similarity', 0):.1f}%")

        print(f"\nSuggested tags ({len(tags)}):")
        for i, tag in enumerate(tags, 1):
            print(f"  {i}. {tag}")

        print(f"\nOptions:")
        print(f"  [a] Approve all tags")
        print(f"  [e] Edit tags")
        print(f"  [r] Reject (skip tagging)")
        print(f"  [q] Quit workflow")

        choice = input("\nYour choice: ").lower().strip()

        if choice == 'a':
            return tags
        elif choice == 'e':
            # Simple editing: enter tags separated by commas
            print("Enter tags (comma-separated):")
            user_input = input("> ")
            return [t.strip() for t in user_input.split(',') if t.strip()]
        elif choice == 'r':
            return None
        elif choice == 'q':
            raise KeyboardInterrupt("User quit workflow")
        else:
            return tags  # Default to approve

    def _save_processing_manifest(self):
        """Save processing manifest to JSON file."""
        manifest_path = self.sorted_dir / f"manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        manifest = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'configuration': {
                'inbox': str(self.inbox_dir),
                'sorted': str(self.sorted_dir),
                'batch_size': self.config['workflow']['batch_size'],
                'content_analysis_enabled': self.config['content_analysis']['enabled'],
                'nas_sync_enabled': self.config['sync']['enabled']
            }
        }

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        logger.info(f"Processing manifest saved: {manifest_path}")

    def _print_final_report(self):
        """Print final processing report."""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        print(f"\n{'='*60}")
        print("Processing Complete!")
        print(f"{'='*60}")
        print(f"Total images:        {self.stats['total_images']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Skipped (existing):  {self.stats['skipped']}")
        print(f"Failed:              {self.stats['failed']}")
        print(f"")
        print(f"Tags found:          {self.stats['tags_found']}")
        print(f"Tags approved:       {self.stats['tags_approved']}")
        print(f"Content analyzed:    {self.stats['content_analyzed']}")
        print(f"Synced to NAS:       {self.stats['synced_to_nas']}")
        print(f"")
        print(f"Processing time:     {duration:.1f} seconds ({duration/60:.1f} minutes)")
        if self.stats['processed'] > 0:
            print(f"Average per image:   {duration/self.stats['processed']:.2f} seconds")
        print(f"{'='*60}\n")
```

## Testing Strategy

### Unit Tests
- [ ] Test each stage in isolation
- [ ] Mock external dependencies (API clients, file operations)
- [ ] Test error handling for each stage
- [ ] Test batch processing logic

### Integration Tests
- [ ] Test complete workflow with 10 sample images
- [ ] Verify XMP sidecars created correctly
- [ ] Verify files moved to correct categories
- [ ] Verify preference learning records movements

### Manual Testing
- [ ] Process 100 real anime images
- [ ] Test tag review interface (accept/edit/reject)
- [ ] Verify NAS sync works correctly
- [ ] Test resume functionality
- [ ] Verify manifest generation

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Complete workflow processes images end-to-end
- [ ] Unit tests pass with 80%+ coverage
- [ ] Integration test with 10 sample images succeeds
- [ ] Manual test with 100 images completes successfully
- [ ] Error handling prevents workflow crashes
- [ ] Progress reporting is clear and accurate
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-002 (Booru search)
- STORY-003 (XMP writer)
- STORY-004 (Content analysis)
- STORY-005 (Preference learning)
- STORY-006 (NAS sync)

**Blocks:**
- STORY-011 (End-to-end testing)

## Notes

- This is the main integration point for all components
- Workflow should be modular - each stage can be skipped
- Consider adding web UI in future for tag review
- Manifest file useful for auditing and troubleshooting

## Risks

- **Medium Risk:** Long-running workflow may timeout or crash
  - *Mitigation:* Checkpoint/resume support, error recovery

## Related Files

- `/src/workflow/orchestrator.py`
- `/src/workflow/batch_processor.py`
- `/tests/test_workflow/test_orchestrator.py`
- `/src/main.py` (CLI entry point)

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
