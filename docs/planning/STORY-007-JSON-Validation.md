# STORY-007: JSON Validation for uma.json Files

**Epic:** EPIC-001
**Story Points:** 2
**Priority:** P3 - Low
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 1 day

## User Story

As a **user**, I want to **validate and filter uma.json files to remove support cards** so that **I only keep character data and exclude unwanted entries**.

## User Story

As a **user**, I want to **validate and filter uma.json files to remove support cards** so that **I only keep character data and exclude unwanted entries from my Uma Musume dataset**.

## Acceptance Criteria

### AC1: JSON Schema Validation
- [ ] Define JSON schema for uma.json files
- [ ] Validate required fields: `name`, `slug` (optional)
- [ ] Validate field types (strings, numbers, arrays, etc.)
- [ ] Report specific validation errors with file path and reason
- [ ] Continue processing other files if one fails validation

### AC2: Content Filtering
- [ ] Filter out files where `name` contains "support card" (case-insensitive)
- [ ] Filter out files where `slug` contains "support_card" (case-insensitive)
- [ ] Support additional custom filter patterns via configuration
- [ ] Allow whitelist mode (only keep matching files)

### AC3: Parallel Processing
- [ ] Process multiple JSON files concurrently
- [ ] Use ThreadPoolExecutor with 8 workers (configurable)
- [ ] Target performance: 1,000 files in 2-3 seconds
- [ ] Progress reporting during processing

### AC4: Output Organization
- [ ] Copy valid files to `validated/` subdirectory
- [ ] Preserve directory structure (optional)
- [ ] Generate report of filtered files
- [ ] Generate summary statistics

### AC5: Error Reporting
- [ ] Log invalid JSON files with parse errors
- [ ] Log filtered files with reason (support card, etc.)
- [ ] Generate CSV report of all processed files
- [ ] Summary: valid count, filtered count, error count

## Technical Implementation

### UmaJsonValidator Class

```python
# src/utils/uma_json_validator.py
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import jsonschema
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from tqdm import tqdm
import csv

logger = logging.getLogger(__name__)

class UmaJsonValidator:
    """Validator for uma.json files with support card filtering."""

    # JSON schema for uma.json files
    UMA_SCHEMA = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "slug": {"type": "string"},
            "id": {"type": ["integer", "string"]},
            "rarity": {"type": ["integer", "string"]},
            "attributes": {"type": "object"}
        },
        "required": ["name"]
    }

    def __init__(self, config: Optional[Dict] = None):
        """Initialize validator.

        Args:
            config: Optional configuration dict with:
                - filter_patterns: List of patterns to filter
                - workers: Number of parallel workers
                - preserve_structure: Preserve directory structure
        """
        self.config = config or {}
        self.filter_patterns = self.config.get('filter_patterns', [
            'support card',
            'support_card'
        ])
        self.workers = self.config.get('workers', 8)
        self.preserve_structure = self.config.get('preserve_structure', False)

    def validate_file(self, json_path: Path) -> Tuple[str, Path, Optional[str]]:
        """Validate a single JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            Tuple of (status, path, error_message)
            Status: 'valid', 'filtered', 'error'
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Schema validation
            try:
                jsonschema.validate(instance=data, schema=self.UMA_SCHEMA)
            except jsonschema.ValidationError as e:
                return ('error', json_path, f"Schema validation failed: {e.message}")

            # Content filtering
            name = data.get('name', '').lower()
            slug = data.get('slug', '').lower()

            for pattern in self.filter_patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in name or pattern_lower in slug:
                    return ('filtered', json_path, f"Matched filter pattern: {pattern}")

            # Passed all checks
            return ('valid', json_path, None)

        except json.JSONDecodeError as e:
            return ('error', json_path, f"Invalid JSON: {e}")
        except Exception as e:
            return ('error', json_path, f"Unexpected error: {e}")

    def validate_batch(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        pattern: str = "uma*.json"
    ) -> Dict:
        """Validate multiple JSON files in parallel.

        Args:
            input_dir: Directory containing JSON files
            output_dir: Optional directory to copy valid files
            pattern: Glob pattern for JSON files

        Returns:
            Dict with validation results and statistics
        """
        # Find all matching JSON files
        json_files = list(input_dir.rglob(pattern))
        total_files = len(json_files)

        if total_files == 0:
            logger.warning(f"No files matching '{pattern}' found in {input_dir}")
            return {
                'total': 0,
                'valid': 0,
                'filtered': 0,
                'errors': 0,
                'files': []
            }

        logger.info(f"Processing {total_files} JSON files with {self.workers} workers...")

        # Process files in parallel
        results = {'valid': [], 'filtered': [], 'error': []}

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.validate_file, json_path): json_path
                for json_path in json_files
            }

            # Collect results with progress bar
            with tqdm(total=total_files, desc="Validating") as pbar:
                for future in as_completed(future_to_file):
                    status, path, error = future.result()
                    results[status].append({
                        'path': str(path),
                        'error': error
                    })
                    pbar.update(1)

        # Copy valid files to output directory
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Copying {len(results['valid'])} valid files to {output_dir}...")

            for item in results['valid']:
                src_path = Path(item['path'])

                if self.preserve_structure:
                    # Preserve directory structure
                    rel_path = src_path.relative_to(input_dir)
                    dest_path = output_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    # Flat structure
                    dest_path = output_dir / src_path.name

                # Copy file
                import shutil
                shutil.copy2(src_path, dest_path)

        # Generate summary
        summary = {
            'total': total_files,
            'valid': len(results['valid']),
            'filtered': len(results['filtered']),
            'errors': len(results['error']),
            'files': results
        }

        logger.info(
            f"Validation complete: {summary['valid']} valid, "
            f"{summary['filtered']} filtered, {summary['errors']} errors"
        )

        return summary

    def generate_report(self, summary: Dict, report_path: Path):
        """Generate CSV report of validation results.

        Args:
            summary: Summary dict from validate_batch()
            report_path: Path to output CSV file
        """
        with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Status', 'File Path', 'Error/Reason'])

            # Write all results
            for status in ['valid', 'filtered', 'error']:
                for item in summary['files'][status]:
                    writer.writerow([
                        status,
                        item['path'],
                        item.get('error', '')
                    ])

        logger.info(f"Report written to {report_path}")

    def print_summary(self, summary: Dict):
        """Print summary statistics to console.

        Args:
            summary: Summary dict from validate_batch()
        """
        print("\n" + "="*60)
        print("Uma JSON Validation Summary")
        print("="*60)
        print(f"Total files:     {summary['total']:>6}")
        print(f"Valid files:     {summary['valid']:>6} ({summary['valid']/summary['total']*100:.1f}%)")
        print(f"Filtered files:  {summary['filtered']:>6} ({summary['filtered']/summary['total']*100:.1f}%)")
        print(f"Errors:          {summary['errors']:>6} ({summary['errors']/summary['total']*100:.1f}%)")
        print("="*60)

        # Show sample filtered files
        if summary['filtered'] > 0:
            print("\nSample filtered files:")
            for item in summary['files']['filtered'][:5]:
                print(f"  - {Path(item['path']).name}: {item['error']}")
            if summary['filtered'] > 5:
                print(f"  ... and {summary['filtered'] - 5} more")

        # Show sample errors
        if summary['errors'] > 0:
            print("\nSample errors:")
            for item in summary['files']['error'][:5]:
                print(f"  - {Path(item['path']).name}: {item['error']}")
            if summary['errors'] > 5:
                print(f"  ... and {summary['errors'] - 5} more")

        print()
```

### CLI Interface

```python
# src/utils/uma_validator_cli.py
import argparse
from pathlib import Path
from src.utils.uma_json_validator import UmaJsonValidator
import sys

def main():
    parser = argparse.ArgumentParser(
        description='Validate and filter uma.json files'
    )
    parser.add_argument(
        'input_dir',
        type=Path,
        help='Directory containing JSON files'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output directory for valid files'
    )
    parser.add_argument(
        '-p', '--pattern',
        default='uma*.json',
        help='Glob pattern for JSON files (default: uma*.json)'
    )
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=8,
        help='Number of parallel workers (default: 8)'
    )
    parser.add_argument(
        '--preserve-structure',
        action='store_true',
        help='Preserve directory structure in output'
    )
    parser.add_argument(
        '--report',
        type=Path,
        help='Path to CSV report file'
    )
    parser.add_argument(
        '--filter',
        action='append',
        dest='filter_patterns',
        help='Additional filter patterns (can be used multiple times)'
    )

    args = parser.parse_args()

    # Validate input directory
    if not args.input_dir.exists():
        print(f"Error: Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    # Build config
    config = {
        'workers': args.workers,
        'preserve_structure': args.preserve_structure
    }

    if args.filter_patterns:
        config['filter_patterns'] = [
            'support card',
            'support_card'
        ] + args.filter_patterns

    # Run validation
    validator = UmaJsonValidator(config)
    summary = validator.validate_batch(
        input_dir=args.input_dir,
        output_dir=args.output,
        pattern=args.pattern
    )

    # Print summary
    validator.print_summary(summary)

    # Generate report if requested
    if args.report:
        validator.generate_report(summary, args.report)

    # Exit with error code if there were errors
    if summary['errors'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Usage Examples

```bash
# Validate all uma*.json files in directory
python -m src.utils.uma_validator_cli /path/to/json/files

# Validate and copy valid files to output directory
python -m src.utils.uma_validator_cli /path/to/json/files -o /path/to/validated

# Generate CSV report
python -m src.utils.uma_validator_cli /path/to/json/files --report report.csv

# Custom pattern and additional filters
python -m src.utils.uma_validator_cli /path/to/json/files \
    --pattern "*.json" \
    --filter "test_card" \
    --filter "deprecated"

# Preserve directory structure
python -m src.utils.uma_validator_cli /path/to/json/files \
    -o /path/to/validated \
    --preserve-structure
```

## Testing Strategy

### Unit Tests

```python
# tests/test_utils/test_uma_json_validator.py
def test_validate_valid_file(tmp_path):
    # Create valid uma.json
    json_file = tmp_path / "uma_001.json"
    json_file.write_text(json.dumps({
        "name": "Special Week",
        "slug": "special-week",
        "rarity": 3
    }))

    validator = UmaJsonValidator()
    status, path, error = validator.validate_file(json_file)

    assert status == 'valid'
    assert error is None

def test_validate_support_card_filtered(tmp_path):
    # Create support card file
    json_file = tmp_path / "uma_002.json"
    json_file.write_text(json.dumps({
        "name": "Support Card: Trainer",
        "slug": "support-card-trainer"
    }))

    validator = UmaJsonValidator()
    status, path, error = validator.validate_file(json_file)

    assert status == 'filtered'
    assert 'support card' in error.lower()

def test_validate_invalid_json(tmp_path):
    # Create invalid JSON file
    json_file = tmp_path / "uma_003.json"
    json_file.write_text("{invalid json")

    validator = UmaJsonValidator()
    status, path, error = validator.validate_file(json_file)

    assert status == 'error'
    assert 'Invalid JSON' in error

def test_batch_validation(tmp_path):
    # Create mix of valid, filtered, and invalid files
    valid_file = tmp_path / "uma_valid.json"
    valid_file.write_text(json.dumps({"name": "Character A"}))

    filtered_file = tmp_path / "uma_support.json"
    filtered_file.write_text(json.dumps({"name": "Support Card B"}))

    invalid_file = tmp_path / "uma_invalid.json"
    invalid_file.write_text("{bad")

    validator = UmaJsonValidator()
    summary = validator.validate_batch(tmp_path)

    assert summary['total'] == 3
    assert summary['valid'] == 1
    assert summary['filtered'] == 1
    assert summary['errors'] == 1
```

### Performance Tests

```python
def test_batch_performance(tmp_path):
    """Verify 1,000 files processed in <5 seconds."""
    # Generate 1,000 test JSON files
    for i in range(1000):
        json_file = tmp_path / f"uma_{i:04d}.json"
        json_file.write_text(json.dumps({
            "name": f"Character {i}",
            "slug": f"char-{i}"
        }))

    import time
    validator = UmaJsonValidator({'workers': 8})

    start = time.time()
    summary = validator.validate_batch(tmp_path)
    elapsed = time.time() - start

    assert summary['total'] == 1000
    assert elapsed < 5.0  # Should complete in under 5 seconds
    print(f"Processed 1,000 files in {elapsed:.2f} seconds")
```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests pass with 85%+ coverage
- [ ] Performance test: 1,000 files in <5 seconds
- [ ] CLI interface implemented and documented
- [ ] CSV report generation working
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-001 (Project setup)

**Blocks:**
- None (independent utility)

## Notes

- This is a utility feature specific to Uma Musume data
- Can be generalized for other JSON validation tasks
- ThreadPoolExecutor provides good parallelism for I/O-bound tasks
- Consider adding support for custom JSON schemas

## Risks

- **Low Risk:** Memory usage with very large JSON files
  - *Mitigation:* Process files one at a time (already implemented)

## Related Files

- `/src/utils/uma_json_validator.py`
- `/src/utils/uma_validator_cli.py`
- `/tests/test_utils/test_uma_json_validator.py`

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
