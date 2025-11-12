"""ExifTool wrapper for writing XMP sidecar files."""

import exiftool
from pathlib import Path
from typing import List, Dict, Optional
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class ExifToolWrapper:
    """Wrapper for ExifTool with stay_open mode for high-performance batch processing."""

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
                version = et.execute('-ver').strip()
                logger.info(f"ExifTool version: {version}")

                # Check minimum version (11.0+)
                try:
                    version_num = float(version.split('.')[0])
                    if version_num < 11:
                        logger.warning(f"ExifTool {version} may be outdated. Recommend 11.0+")
                except ValueError:
                    logger.warning(f"Could not parse ExifTool version: {version}")

        except FileNotFoundError:
            raise RuntimeError(
                "ExifTool not found. Please install ExifTool and ensure it's in PATH, "
                "or specify the path in configuration."
            )
        except Exception as e:
            raise RuntimeError(f"ExifTool verification failed: {e}")

    def __enter__(self):
        """Start ExifTool in stay_open mode for batch processing."""
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
        source_url: Optional[str] = None,
        sidecar_format: str = "{filename}.xmp"
    ) -> bool:
        """Write metadata to XMP sidecar file.

        Args:
            image_path: Path to image file
            tags: List of tags to write
            description: Optional description text
            rating: Optional rating (0-5)
            source_url: Optional source URL
            sidecar_format: Sidecar naming format (default: image.jpg.xmp)

        Returns:
            True if successful, False otherwise
        """
        if not self.et:
            logger.error("ExifTool not started. Use context manager or call start()")
            return False

        try:
            # Determine sidecar path
            if "{filename}.xmp" in sidecar_format:
                sidecar_path = Path(str(image_path) + '.xmp')
            else:
                sidecar_path = image_path.with_suffix('.xmp')

            # Build ExifTool parameters
            params = [
                '-o', str(sidecar_path),  # Output to sidecar
                '-overwrite_original',     # No backup files
            ]

            # Write tags to multiple fields for maximum compatibility
            if tags:
                for tag in tags:
                    # Sanitize tag
                    safe_tag = self._sanitize_tag(tag)
                    if safe_tag:
                        # Write to all three tag fields
                        params.extend([
                            f'-XMP-digiKam:TagsList={safe_tag}',
                            f'-IPTC:Keywords={safe_tag}',
                            f'-XMP-dc:Subject={safe_tag}',
                        ])

            # Optional description field
            if description:
                safe_desc = self._sanitize_text(description)
                params.append(f'-XMP-dc:Description={safe_desc}')

            # Optional rating field (0-5 stars)
            if rating is not None:
                if 0 <= rating <= 5:
                    params.append(f'-XMP-xmp:Rating={rating}')
                else:
                    logger.warning(f"Rating {rating} out of range (0-5), skipping")

            # Optional source URL
            if source_url:
                safe_url = self._sanitize_text(source_url)
                params.append(f'-XMP-dc:Source={safe_url}')

            # Add image path as final parameter
            params.append(str(image_path))

            # Execute ExifTool
            result = self.et.execute(*params)

            # Check for errors in output
            if result and ('error' in result.lower() or 'warning' in result.lower()):
                logger.warning(f"ExifTool output for {image_path.name}: {result}")

            # Verify sidecar was created
            if not sidecar_path.exists():
                logger.error(f"XMP sidecar not created: {sidecar_path}")
                return False

            # Validate XMP is well-formed
            if not self._validate_xmp(sidecar_path):
                logger.warning(f"XMP validation failed: {sidecar_path}")
                # Don't fail - Immich may still read it

            logger.debug(f"Created XMP sidecar: {sidecar_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to write XMP for {image_path.name}: {e}", exc_info=True)
            return False

    def write_xmp_batch(
        self,
        image_metadata: List[Dict],
        progress_callback=None
    ) -> Dict[str, int]:
        """Write XMP sidecars for multiple images in batch mode.

        Args:
            image_metadata: List of dicts with keys:
                - image_path: Path object
                - tags: List[str]
                - description: Optional[str]
                - rating: Optional[int]
                - source_url: Optional[str]
            progress_callback: Optional callback function(current, total)

        Returns:
            Dict with 'success', 'failed', 'total' counts
        """
        if not self.et:
            logger.error("ExifTool not started. Use context manager.")
            return {'success': 0, 'failed': len(image_metadata), 'total': len(image_metadata)}

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
                source_url=metadata.get('source_url'),
                sidecar_format=metadata.get('sidecar_format', '{filename}.xmp')
            ):
                success += 1
            else:
                failed += 1

            # Progress callback
            if progress_callback:
                progress_callback(idx, total)

            # Progress logging every 100 images
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")

        logger.info(f"XMP batch complete: {success} success, {failed} failed")

        return {
            'success': success,
            'failed': failed,
            'total': total
        }

    def read_xmp_tags(self, image_path: Path) -> List[str]:
        """Read existing tags from image or XMP sidecar.

        Args:
            image_path: Path to image file

        Returns:
            List of existing tags
        """
        if not self.et:
            logger.error("ExifTool not started")
            return []

        try:
            # Check for XMP sidecar first
            sidecar_path = Path(str(image_path) + '.xmp')
            if sidecar_path.exists():
                metadata = self.et.get_metadata(str(sidecar_path))
            else:
                metadata = self.et.get_metadata(str(image_path))

            # Extract tags from various fields
            tags = []

            # digiKam tags (primary)
            if 'XMP:TagsList' in metadata:
                digikam_tags = metadata['XMP:TagsList']
                if isinstance(digikam_tags, list):
                    tags.extend(digikam_tags)
                else:
                    tags.append(str(digikam_tags))

            # IPTC Keywords
            if 'IPTC:Keywords' in metadata:
                iptc_tags = metadata['IPTC:Keywords']
                if isinstance(iptc_tags, list):
                    tags.extend(iptc_tags)
                else:
                    tags.append(str(iptc_tags))

            # Remove duplicates while preserving order
            seen = set()
            unique_tags = []
            for tag in tags:
                if tag and tag not in seen:
                    seen.add(tag)
                    unique_tags.append(tag)

            return unique_tags

        except Exception as e:
            logger.error(f"Failed to read tags from {image_path}: {e}")
            return []

    @staticmethod
    def _sanitize_tag(tag: str) -> str:
        """Sanitize tag for XMP format.

        Removes or escapes characters that may cause issues:
        - Control characters
        - Leading/trailing whitespace
        - Multiple consecutive spaces
        - XML special characters

        Args:
            tag: Raw tag string

        Returns:
            Sanitized tag string
        """
        if not tag:
            return ""

        # Remove control characters
        tag = ''.join(char for char in tag if ord(char) >= 32)

        # Trim and normalize spaces
        tag = ' '.join(tag.split())

        # Don't escape XML characters - ExifTool handles this
        # (Previous versions had manual escaping but ExifTool does it automatically)

        return tag

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Sanitize general text fields (description, URL, etc).

        Args:
            text: Raw text string

        Returns:
            Sanitized text string
        """
        if not text:
            return ""

        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

        # Normalize whitespace
        text = ' '.join(text.split())

        return text

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
            logger.debug(f"XMP parse error in {xmp_path.name}: {e}")
            return False
        except Exception as e:
            logger.debug(f"XMP validation error in {xmp_path.name}: {e}")
            return False

    def start(self):
        """Start ExifTool process (if not using context manager)."""
        if not self.et:
            self.et = exiftool.ExifTool(executable_=self.exiftool_path)
            self.et.start()
            logger.info("ExifTool started")

    def stop(self):
        """Stop ExifTool process (if not using context manager)."""
        if self.et:
            self.et.terminate()
            self.et = None
            logger.info("ExifTool stopped")
