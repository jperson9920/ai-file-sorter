"""NAS synchronization using Robocopy on Windows."""

import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging
import platform

logger = logging.getLogger(__name__)


class NASSyncManager:
    """Manager for syncing files to NAS using Robocopy (Windows only)."""

    def __init__(self, config: Dict):
        """Initialize NAS sync manager.

        Args:
            config: Configuration dict with sync settings
        """
        self.config = config.get('sync', {})
        self.enabled = self.config.get('enabled', False)
        self.robocopy_options = self.config.get('robocopy_options', '/MIR /XO /R:3 /W:5')

        if platform.system() != 'Windows':
            logger.warning("NASSyncManager is Windows-only (requires Robocopy)")
            self.enabled = False

        logger.info(f"NASSyncManager initialized (enabled={self.enabled})")

    def sync_directory(
        self,
        source_dir: Path,
        destination_dir: Path,
        dry_run: bool = False
    ) -> Dict:
        """Sync directory to NAS using Robocopy.

        Args:
            source_dir: Source directory path
            destination_dir: Destination directory path (NAS)
            dry_run: If True, show what would be synced without actually syncing

        Returns:
            Dict with sync results:
                - success: bool
                - files_copied: int
                - files_skipped: int
                - errors: int
                - output: str
        """
        if not self.enabled:
            logger.warning("NAS sync is disabled")
            return {
                'success': False,
                'error': 'NAS sync is disabled',
                'files_copied': 0,
                'files_skipped': 0,
                'errors': 0
            }

        if not source_dir.exists():
            logger.error(f"Source directory does not exist: {source_dir}")
            return {
                'success': False,
                'error': f'Source directory not found: {source_dir}',
                'files_copied': 0,
                'files_skipped': 0,
                'errors': 0
            }

        try:
            # Build Robocopy command
            options_list = self.robocopy_options.split()

            if dry_run:
                options_list.append('/L')  # List only mode

            cmd = [
                'robocopy',
                str(source_dir),
                str(destination_dir),
                *options_list
            ]

            logger.info(f"Starting sync: {source_dir} -> {destination_dir}")
            logger.debug(f"Robocopy command: {' '.join(cmd)}")

            # Run Robocopy
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            output = result.stdout + result.stderr

            # Parse Robocopy output (exit codes 0-7 are success)
            success = result.returncode < 8

            # Try to parse stats from output
            files_copied = 0
            files_skipped = 0
            errors = 0

            for line in output.split('\n'):
                if 'Copied :' in line:
                    try:
                        files_copied = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass
                elif 'Skipped :' in line:
                    try:
                        files_skipped = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass
                elif 'FAILED :' in line:
                    try:
                        errors = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass

            logger.info(
                f"Sync {'complete' if success else 'failed'}: "
                f"{files_copied} copied, {files_skipped} skipped, {errors} errors"
            )

            return {
                'success': success,
                'files_copied': files_copied,
                'files_skipped': files_skipped,
                'errors': errors,
                'output': output,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error("Sync timeout expired")
            return {
                'success': False,
                'error': 'Sync timeout (>1 hour)',
                'files_copied': 0,
                'files_skipped': 0,
                'errors': 1
            }
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'files_copied': 0,
                'files_skipped': 0,
                'errors': 1
            }

    def is_enabled(self) -> bool:
        """Check if NAS sync is enabled.

        Returns:
            True if enabled, False otherwise
        """
        return self.enabled
