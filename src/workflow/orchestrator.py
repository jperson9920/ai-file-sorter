"""Main workflow orchestrator integrating all components."""

from pathlib import Path
from typing import Dict, List, Optional
import logging
import hashlib
from PIL import Image

from ..booru import BooruSearcher
from ..xmp_writer import ExifToolWrapper, MetadataBuilder
from ..content_analysis import ContentAnalyzer
from ..learning import PreferenceDatabase
from .nas_sync import NASSyncManager

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Main orchestrator for the complete image tagging workflow."""

    def __init__(self, config: Dict):
        """Initialize workflow orchestrator.

        Args:
            config: Complete configuration dictionary
        """
        self.config = config

        # Initialize components
        logger.info("Initializing workflow components...")

        self.booru_searcher = BooruSearcher(config)
        self.content_analyzer = ContentAnalyzer(config)
        self.nas_sync = NASSyncManager(config)

        # Preference learning
        learning_config = config.get('learning', {})
        db_path = learning_config.get('database_path', 'data/preferences.db')
        self.preference_db = PreferenceDatabase(db_path)

        # Workflow settings
        workflow_config = config.get('workflow', {})
        self.batch_size = workflow_config.get('batch_size', 100)
        self.enable_gui_review = workflow_config.get('enable_gui_review', False)
        self.auto_approve = workflow_config.get('auto_approve_high_confidence', False)

        logger.info("Workflow orchestrator initialized")

    def _hash_file(self, file_path: Path) -> str:
        """Generate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest string
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def process_image(
        self,
        image_path: Path,
        skip_existing: bool = True
    ) -> Dict:
        """Process a single image through the complete workflow.

        Args:
            image_path: Path to image file
            skip_existing: Skip if XMP sidecar already exists

        Returns:
            Dict with processing results
        """
        result = {
            'image_path': str(image_path),
            'status': 'pending',
            'booru_match': False,
            'content_analyzed': False,
            'xmp_written': False,
            'tags': []
        }

        try:
            # Check if XMP already exists
            xmp_path = Path(str(image_path) + '.xmp')
            if skip_existing and xmp_path.exists():
                logger.debug(f"Skipping {image_path.name} - XMP exists")
                result['status'] = 'skipped'
                return result

            # Step 1: Reverse image search for tags
            logger.info(f"Processing: {image_path.name}")
            booru_result = await self.booru_searcher.search_and_tag(image_path)

            if booru_result['status'] == 'success':
                result['booru_match'] = True
                result['similarity'] = booru_result['similarity']

            # Step 2: Content analysis (if enabled)
            content_result = None
            if self.content_analyzer.is_enabled():
                content_result = self.content_analyzer.analyze_image(image_path)
                if content_result['status'] == 'success':
                    result['content_analyzed'] = True
                    result['style'] = content_result['style']
                    result['persons_detected'] = content_result['persons_detected']

            # Step 3: Build metadata
            metadata = None

            if booru_result['status'] == 'success' and booru_result.get('flat_tags'):
                # Use booru tags as primary source
                metadata = MetadataBuilder.build_from_booru_tags(
                    image_path,
                    booru_result,
                    include_rating=self.config.get('xmp', {}).get('include_rating', False)
                )

            # Merge with content analysis if available
            if content_result and content_result['status'] == 'success':
                content_metadata = MetadataBuilder.build_from_content_analysis(
                    image_path,
                    content_result
                )

                if metadata:
                    metadata = MetadataBuilder.merge_metadata(metadata, content_metadata)
                else:
                    metadata = content_metadata

            # Step 4: Write XMP sidecar
            if metadata and metadata['tags']:
                with ExifToolWrapper() as et:
                    success = et.write_xmp_sidecar(
                        image_path=metadata['image_path'],
                        tags=metadata['tags'],
                        description=metadata.get('description'),
                        rating=metadata.get('rating'),
                        source_url=metadata.get('source_url')
                    )

                    if success:
                        result['xmp_written'] = True
                        result['tags'] = metadata['tags']
                        result['status'] = 'success'
                    else:
                        result['status'] = 'error'
                        result['error'] = 'Failed to write XMP'
            else:
                result['status'] = 'no_tags'
                result['error'] = 'No tags found to write'

            # Step 5: Learn from this processing
            if result['status'] == 'success':
                file_hash = self._hash_file(image_path)
                style = content_result.get('style') if content_result else None
                persons = content_result.get('persons_detected') if content_result else None

                # This would be updated when user actually moves the file
                # For now, just record what was suggested
                # self.preference_db.record_movement(...)

            return result

        except Exception as e:
            logger.error(f"Failed to process {image_path}: {e}", exc_info=True)
            result['status'] = 'error'
            result['error'] = str(e)
            return result

    async def process_batch(
        self,
        image_paths: List[Path],
        skip_existing: bool = True,
        progress_callback=None
    ) -> Dict:
        """Process multiple images in batch.

        Args:
            image_paths: List of image file paths
            skip_existing: Skip images with existing XMP sidecars
            progress_callback: Optional callback(current, total)

        Returns:
            Dict with batch processing summary
        """
        total = len(image_paths)
        results = []

        logger.info(f"Processing batch of {total} images...")

        for idx, image_path in enumerate(image_paths, 1):
            result = await self.process_image(image_path, skip_existing)
            results.append(result)

            if progress_callback:
                progress_callback(idx, total)

            if idx % 10 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")

        # Summary statistics
        summary = {
            'total': total,
            'success': sum(1 for r in results if r['status'] == 'success'),
            'skipped': sum(1 for r in results if r['status'] == 'skipped'),
            'no_tags': sum(1 for r in results if r['status'] == 'no_tags'),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'results': results
        }

        logger.info(
            f"Batch complete: {summary['success']} success, "
            f"{summary['skipped']} skipped, "
            f"{summary['no_tags']} no tags, "
            f"{summary['errors']} errors"
        )

        return summary

    def sync_to_nas(self, source_dir: Path, dry_run: bool = False) -> Dict:
        """Sync processed images to NAS.

        Args:
            source_dir: Source directory with processed images
            dry_run: If True, show what would be synced

        Returns:
            Dict with sync results
        """
        if not self.nas_sync.is_enabled():
            logger.warning("NAS sync is not enabled")
            return {'success': False, 'error': 'NAS sync disabled'}

        nas_path = Path(self.config.get('directories', {}).get('nas_path', ''))

        if not nas_path:
            logger.error("NAS path not configured")
            return {'success': False, 'error': 'NAS path not configured'}

        return self.nas_sync.sync_directory(source_dir, nas_path, dry_run)

    def get_statistics(self) -> Dict:
        """Get processing statistics.

        Returns:
            Dict with various statistics
        """
        stats = {
            'booru_cache': self.booru_searcher.get_cache_stats(),
            'preferences': self.preference_db.get_stats()
        }

        return stats
