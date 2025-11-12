"""JSON validation with parallel processing for uma.json files."""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


class JSONValidator:
    """Parallel JSON validator for filtering support card files."""

    def __init__(self, max_workers: int = 8):
        """Initialize JSON validator.

        Args:
            max_workers: Number of parallel worker threads
        """
        self.max_workers = max_workers
        logger.info(f"JSONValidator initialized with {max_workers} workers")

    def validate_file(self, json_path: Path) -> Tuple[str, Path, Optional[str]]:
        """Validate a single JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            Tuple of (status, path, error_message)
            status: 'valid', 'invalid', 'filtered', 'error'
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check required fields
            if 'name' not in data:
                return ('invalid', json_path, 'Missing required field: name')

            name = data.get('name', '').lower()
            slug = data.get('slug', '').lower()

            # Filter support cards (case-insensitive)
            if 'support card' in name or 'support_card' in slug:
                return ('valid', json_path, None)
            else:
                return ('filtered', json_path, 'Not a support card')

        except json.JSONDecodeError as e:
            return ('error', json_path, f'JSON parse error: {e}')
        except Exception as e:
            return ('error', json_path, str(e))

    def validate_batch(
        self,
        json_paths: List[Path],
        progress_callback=None
    ) -> Dict:
        """Validate multiple JSON files in parallel.

        Args:
            json_paths: List of JSON file paths
            progress_callback: Optional callback(current, total)

        Returns:
            Dict with validation results:
                - valid: List of valid file paths
                - invalid: List of (path, error) tuples
                - filtered: List of filtered file paths
                - errors: List of (path, error) tuples
        """
        results = {
            'valid': [],
            'invalid': [],
            'filtered': [],
            'errors': []
        }

        total = len(json_paths)
        completed = 0

        logger.info(f"Validating {total} JSON files with {self.max_workers} workers...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.validate_file, path): path
                for path in json_paths
            }

            # Process completed tasks
            for future in as_completed(futures):
                status, path, error = future.result()

                if status == 'valid':
                    results['valid'].append(path)
                elif status == 'invalid':
                    results['invalid'].append((path, error))
                elif status == 'filtered':
                    results['filtered'].append(path)
                elif status == 'error':
                    results['errors'].append((path, error))

                completed += 1

                if progress_callback:
                    progress_callback(completed, total)

                if completed % 100 == 0:
                    logger.info(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")

        logger.info(
            f"Validation complete: {len(results['valid'])} valid, "
            f"{len(results['filtered'])} filtered, "
            f"{len(results['invalid'])} invalid, "
            f"{len(results['errors'])} errors"
        )

        return results

    def find_uma_json_files(self, directory: Path) -> List[Path]:
        """Find all uma*.json files in directory recursively.

        Args:
            directory: Root directory to search

        Returns:
            List of JSON file paths
        """
        json_files = list(directory.rglob('uma*.json'))
        logger.info(f"Found {len(json_files)} uma*.json files in {directory}")
        return json_files
