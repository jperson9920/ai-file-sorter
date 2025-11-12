# STORY-006: Windows-to-NAS Sync Automation

**Epic:** EPIC-001
**Story Points:** 3
**Priority:** P2 - Medium
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 1-2 days

## User Story

As a **user**, I want to **automatically sync my sorted and tagged images to my Synology NAS** so that **Immich can access them and my master library stays updated**.

## Acceptance Criteria

### AC1: Robocopy Integration
- [ ] Implement Windows Robocopy wrapper for file synchronization
- [ ] Use `/MIR` (mirror) option for exact replica
- [ ] Use `/XO` (exclude older) to preserve newer files
- [ ] Use `/R:3 /W:5` for retry logic (3 retries, 5 second wait)
- [ ] Support dry-run mode for testing without actual sync

### AC2: Sync Configuration
- [ ] Configure source directory (local sorted images)
- [ ] Configure destination directory (NAS path or mapped drive)
- [ ] Support both UNC paths (`\\NAS\share`) and mapped drives (`Z:\`)
- [ ] Verify source and destination exist before sync
- [ ] Support file/folder exclusion patterns

### AC3: Incremental Sync
- [ ] Only sync changed/new files (not full copy each time)
- [ ] Detect and sync XMP sidecars alongside images
- [ ] Preserve directory structure
- [ ] Handle file renames and moves
- [ ] Log all sync operations

### AC4: Error Handling
- [ ] Detect network connectivity issues
- [ ] Retry failed transfers with exponential backoff
- [ ] Handle insufficient disk space on destination
- [ ] Continue sync on single file failures
- [ ] Generate detailed error report

### AC5: Progress Reporting
- [ ] Show progress during sync (files transferred, MB/s)
- [ ] Estimate time remaining
- [ ] Display summary after sync (files copied, updated, deleted)
- [ ] Log sync duration and performance metrics

### AC6: Validation
- [ ] Verify file sizes match after sync
- [ ] Optional: Verify checksums for critical files
- [ ] Detect sync failures (incomplete transfers)
- [ ] Alert user to any sync issues

## Technical Implementation

### RobocopySync Class

```python
# src/workflow/nas_sync.py
import subprocess
from pathlib import Path
from typing import List, Optional, Dict
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class RobocopySync:
    """Windows Robocopy-based sync to NAS."""

    def __init__(self, config: Dict):
        """Initialize sync manager.

        Args:
            config: Sync configuration dict
        """
        self.source_dir = Path(config['source_dir'])
        self.dest_dir = Path(config['dest_dir'])
        self.robocopy_options = config.get('robocopy_options', '/MIR /XO /R:3 /W:5')
        self.exclude_files = config.get('exclude_files', [])
        self.exclude_dirs = config.get('exclude_dirs', [])
        self.dry_run = config.get('dry_run', False)

    def validate_paths(self) -> bool:
        """Validate source and destination paths exist.

        Returns:
            True if valid, False otherwise
        """
        if not self.source_dir.exists():
            logger.error(f"Source directory does not exist: {self.source_dir}")
            return False

        # For UNC paths or mapped drives, check parent
        try:
            if not self.dest_dir.exists():
                # Try to create if parent exists
                if self.dest_dir.parent.exists():
                    self.dest_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created destination directory: {self.dest_dir}")
                else:
                    logger.error(f"Destination parent does not exist: {self.dest_dir.parent}")
                    return False
        except Exception as e:
            logger.error(f"Cannot access destination: {e}")
            return False

        return True

    def sync(self, progress_callback: Optional[callable] = None) -> Dict:
        """Perform sync operation.

        Args:
            progress_callback: Optional callback(current, total, speed_mbps)

        Returns:
            Dict with sync results and statistics
        """
        if not self.validate_paths():
            return {'status': 'error', 'error': 'Invalid paths'}

        logger.info(f"Starting sync: {self.source_dir} → {self.dest_dir}")
        start_time = datetime.now()

        # Build Robocopy command
        cmd = self._build_command()

        if self.dry_run:
            logger.info(f"DRY RUN: Would execute: {' '.join(cmd)}")
            return {'status': 'dry_run', 'command': ' '.join(cmd)}

        try:
            # Execute Robocopy
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Parse Robocopy output
            stats = self._parse_robocopy_output(result.stdout)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            stats['duration_seconds'] = duration

            # Robocopy exit codes: 0-7 are success, 8+ are failures
            if result.returncode < 8:
                logger.info(
                    f"Sync completed successfully in {duration:.1f}s: "
                    f"{stats.get('files_copied', 0)} copied, "
                    f"{stats.get('files_skipped', 0)} skipped"
                )
                stats['status'] = 'success'
            else:
                logger.error(f"Sync failed with exit code {result.returncode}")
                stats['status'] = 'error'
                stats['error'] = f"Robocopy exit code: {result.returncode}"

            stats['exit_code'] = result.returncode
            stats['stdout'] = result.stdout
            stats['stderr'] = result.stderr

            return stats

        except Exception as e:
            logger.error(f"Sync failed with exception: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }

    def _build_command(self) -> List[str]:
        """Build Robocopy command with options.

        Returns:
            List of command arguments
        """
        cmd = [
            'robocopy',
            str(self.source_dir),
            str(self.dest_dir)
        ]

        # Add options
        cmd.extend(self.robocopy_options.split())

        # Exclude files
        for pattern in self.exclude_files:
            cmd.extend(['/XF', pattern])

        # Exclude directories
        for pattern in self.exclude_dirs:
            cmd.extend(['/XD', pattern])

        # Log output with details
        cmd.extend(['/V', '/NP'])  # Verbose, no progress percentage

        return cmd

    def _parse_robocopy_output(self, output: str) -> Dict:
        """Parse Robocopy output for statistics.

        Args:
            output: Robocopy stdout

        Returns:
            Dict with parsed statistics
        """
        stats = {
            'dirs_total': 0,
            'files_total': 0,
            'files_copied': 0,
            'files_skipped': 0,
            'files_mismatch': 0,
            'files_failed': 0,
            'bytes_total': 0,
            'bytes_copied': 0,
            'speed_mbps': 0.0
        }

        # Parse summary section
        # Example lines:
        #     Dirs :        10         0        10         0         0         0
        #   Files :       523         5       518         0         0         0
        #   Bytes : 1.234 g   5.6 m   1.229 g         0         0         0

        dirs_match = re.search(r'Dirs\s*:\s*(\d+)\s+(\d+)\s+(\d+)', output)
        if dirs_match:
            stats['dirs_total'] = int(dirs_match.group(1))

        files_match = re.search(r'Files\s*:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', output)
        if files_match:
            stats['files_total'] = int(files_match.group(1))
            stats['files_copied'] = int(files_match.group(2))
            stats['files_skipped'] = int(files_match.group(3))
            stats['files_mismatch'] = int(files_match.group(4))
            stats['files_failed'] = int(files_match.group(5))

        # Parse speed (MB/s)
        speed_match = re.search(r'Speed\s*:\s*([\d.]+)\s+Bytes/sec', output)
        if speed_match:
            bytes_per_sec = float(speed_match.group(1))
            stats['speed_mbps'] = bytes_per_sec / (1024 * 1024)

        return stats

    def test_connection(self) -> bool:
        """Test network connectivity to destination.

        Returns:
            True if destination is accessible
        """
        try:
            # Try to list destination directory
            if self.dest_dir.exists():
                # Try to create a test file
                test_file = self.dest_dir / '.sync_test'
                test_file.touch()
                test_file.unlink()
                logger.info("Connection test successful")
                return True
            else:
                logger.warning("Destination directory not accessible")
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
```

### SMB Mount Helper (Optional)

```python
# src/workflow/smb_mount.py
import subprocess
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SMBMount:
    """Helper for mounting SMB shares on Windows."""

    @staticmethod
    def mount_share(
        unc_path: str,
        drive_letter: str,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> bool:
        """Mount SMB share to drive letter.

        Args:
            unc_path: UNC path like \\\\192.168.1.100\\photos
            drive_letter: Drive letter like Z:
            username: Optional username for authentication
            password: Optional password for authentication

        Returns:
            True if successful
        """
        cmd = ['net', 'use', drive_letter, unc_path]

        if username:
            cmd.extend(['/user:' + username])

        if password:
            cmd.append(password)

        cmd.append('/persistent:yes')  # Reconnect on boot

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"Mounted {unc_path} to {drive_letter}")
                return True
            else:
                logger.error(f"Failed to mount: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Mount failed: {e}")
            return False

    @staticmethod
    def unmount_share(drive_letter: str) -> bool:
        """Unmount SMB share.

        Args:
            drive_letter: Drive letter like Z:

        Returns:
            True if successful
        """
        cmd = ['net', 'use', drive_letter, '/delete']

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Unmounted {drive_letter}")
                return True
            else:
                logger.error(f"Failed to unmount: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Unmount failed: {e}")
            return False

    @staticmethod
    def is_mounted(drive_letter: str) -> bool:
        """Check if drive letter is currently mounted.

        Args:
            drive_letter: Drive letter like Z:

        Returns:
            True if mounted
        """
        drive_path = Path(drive_letter + '\\')
        return drive_path.exists()
```

### Usage Example

```python
# Example: Sync sorted images to NAS
from src.workflow.nas_sync import RobocopySync

config = {
    'source_dir': 'C:\\ImageProcessing\\Sorted',
    'dest_dir': 'Z:\\sorted_images',  # Or \\\\NAS\\photos\\sorted
    'robocopy_options': '/MIR /XO /R:3 /W:5',
    'exclude_files': ['Thumbs.db', '.DS_Store'],
    'exclude_dirs': ['@eaDir'],  # Synology metadata folder
    'dry_run': False
}

sync = RobocopySync(config)

# Test connection first
if sync.test_connection():
    # Perform sync
    result = sync.sync()

    if result['status'] == 'success':
        print(f"Synced {result['files_copied']} files in {result['duration_seconds']:.1f}s")
    else:
        print(f"Sync failed: {result.get('error')}")
```

## Testing Strategy

### Unit Tests

```python
# tests/test_workflow/test_nas_sync.py
def test_build_command():
    config = {
        'source_dir': 'C:\\Source',
        'dest_dir': 'C:\\Dest',
        'robocopy_options': '/MIR /XO',
        'exclude_files': ['*.tmp'],
        'exclude_dirs': ['cache']
    }

    sync = RobocopySync(config)
    cmd = sync._build_command()

    assert 'robocopy' in cmd[0]
    assert 'C:\\Source' in cmd
    assert 'C:\\Dest' in cmd
    assert '/MIR' in cmd
    assert '/XO' in cmd
    assert '/XF' in cmd
    assert '*.tmp' in cmd
    assert '/XD' in cmd
    assert 'cache' in cmd

def test_parse_robocopy_output():
    output = """
      Dirs :        10         0        10         0         0         0
    Files :       523         5       518         0         0         0
    Bytes : 1.234 g   5.6 m   1.229 g         0         0         0
    Speed :           5242880 Bytes/sec.
    """

    sync = RobocopySync({'source_dir': '.', 'dest_dir': '.'})
    stats = sync._parse_robocopy_output(output)

    assert stats['dirs_total'] == 10
    assert stats['files_total'] == 523
    assert stats['files_copied'] == 5
    assert stats['files_skipped'] == 518
    assert stats['speed_mbps'] > 0
```

### Integration Tests

```python
def test_local_sync(tmp_path):
    """Test sync between local directories."""
    source = tmp_path / 'source'
    dest = tmp_path / 'dest'
    source.mkdir()
    dest.mkdir()

    # Create test files
    (source / 'test1.jpg').write_bytes(b'image1')
    (source / 'test2.jpg').write_bytes(b'image2')

    config = {
        'source_dir': str(source),
        'dest_dir': str(dest),
        'robocopy_options': '/MIR /XO',
        'exclude_files': [],
        'exclude_dirs': []
    }

    sync = RobocopySync(config)
    result = sync.sync()

    assert result['status'] == 'success'
    assert (dest / 'test1.jpg').exists()
    assert (dest / 'test2.jpg').exists()
    assert result['files_copied'] >= 2
```

### Manual Testing
- [ ] Test sync to real Synology NAS over network
- [ ] Verify XMP sidecars sync alongside images
- [ ] Test with UNC path and mapped drive
- [ ] Verify incremental sync (only changed files)
- [ ] Test recovery from network interruption
- [ ] Measure sync performance (MB/s)

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests pass with 80%+ coverage
- [ ] Integration test syncs local directories
- [ ] Manual test syncs to real NAS successfully
- [ ] Error handling for network issues
- [ ] Logging implemented for all operations
- [ ] Configuration options documented
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-001 (Project setup)
- STORY-003 (XMP sidecars must exist to sync)

**Blocks:**
- STORY-008 (Workflow orchestration uses sync)

## Notes

- Robocopy is built into Windows (no external dependency)
- `/MIR` mirrors source to destination (deletes extra files in dest)
- Exit codes 0-7 indicate success with different conditions
- Synology creates `@eaDir` folders - should be excluded
- Consider using mapped drive (Z:) for better performance than UNC

## Risks

- **Medium Risk:** Network interruptions during sync
  - *Mitigation:* Robocopy retry logic, resume support

- **Low Risk:** Destination disk full
  - *Mitigation:* Check free space before sync, clear error message

## Related Files

- `/src/workflow/nas_sync.py`
- `/src/workflow/smb_mount.py`
- `/tests/test_workflow/test_nas_sync.py`
- `/config/config.yaml` (sync settings)

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
