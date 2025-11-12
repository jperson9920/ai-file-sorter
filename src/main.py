"""Main entry point for image tagging system."""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger
import logging

logger = None


def main():
    """Main entry point."""
    global logger

    parser = argparse.ArgumentParser(
        description="Automated Image Tagging and File Sorting System"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Process command
    process_parser = subparsers.add_parser(
        'process',
        help='Process images in inbox directory'
    )
    process_parser.add_argument(
        '--auto-approve',
        action='store_true',
        help='Automatically approve all tags without review'
    )
    process_parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip images that already have XMP sidecars'
    )
    process_parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )

    # Sync command
    sync_parser = subparsers.add_parser(
        'sync',
        help='Sync sorted images to NAS'
    )
    sync_parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Show preference learning statistics'
    )
    stats_parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )

    # Export preferences command
    export_parser = subparsers.add_parser(
        'export-preferences',
        help='Export learned preferences to JSON'
    )
    export_parser.add_argument(
        'output',
        help='Output JSON file path'
    )
    export_parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )

    # Reset preferences command
    reset_parser = subparsers.add_parser(
        'reset-preferences',
        help='Reset all learned preferences'
    )
    reset_parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        # Load configuration
        config = load_config(args.config)

        # Setup logging
        logger = setup_logger(config)

        # Execute command
        if args.command == 'process':
            return cmd_process(config, args)
        elif args.command == 'sync':
            return cmd_sync(config, args)
        elif args.command == 'stats':
            return cmd_stats(config, args)
        elif args.command == 'export-preferences':
            return cmd_export_preferences(config, args)
        elif args.command == 'reset-preferences':
            return cmd_reset_preferences(config, args)

    except KeyboardInterrupt:
        if logger:
            logger.info("Operation cancelled by user")
        print("\nOperation cancelled.")
        return 130
    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1

    return 0


def cmd_process(config, args):
    """Process images in inbox."""
    import asyncio
    from pathlib import Path
    from src.workflow import WorkflowOrchestrator

    logger.info("Starting image processing workflow...")

    # Get inbox directory
    inbox = Path(config['directories']['inbox'])
    if not inbox.exists():
        print(f"Error: Inbox directory not found: {inbox}")
        return 1

    # Find image files
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    image_files = [f for f in inbox.rglob('*') if f.suffix.lower() in image_extensions]

    if not image_files:
        print(f"No images found in {inbox}")
        return 0

    print(f"Found {len(image_files)} images to process")

    # Initialize orchestrator
    orchestrator = WorkflowOrchestrator(config)

    # Process batch
    async def run_batch():
        return await orchestrator.process_batch(
            image_files,
            skip_existing=args.skip_existing
        )

    summary = asyncio.run(run_batch())

    # Print summary
    print(f"\nProcessing complete:")
    print(f"  Success: {summary['success']}")
    print(f"  Skipped: {summary['skipped']}")
    print(f"  No tags: {summary['no_tags']}")
    print(f"  Errors: {summary['errors']}")

    return 0


def cmd_sync(config, args):
    """Sync to NAS."""
    from pathlib import Path
    from src.workflow import WorkflowOrchestrator

    logger.info("Starting NAS sync...")

    orchestrator = WorkflowOrchestrator(config)
    sorted_dir = Path(config['directories']['sorted'])

    if not sorted_dir.exists():
        print(f"Error: Sorted directory not found: {sorted_dir}")
        return 1

    print(f"Syncing {sorted_dir} to NAS...")
    result = orchestrator.sync_to_nas(sorted_dir, dry_run=False)

    if result.get('success'):
        print(f"Sync complete: {result['files_copied']} files copied")
        return 0
    else:
        print(f"Sync failed: {result.get('error', 'Unknown error')}")
        return 1


def cmd_stats(config, args):
    """Show preference statistics."""
    from src.workflow import WorkflowOrchestrator
    import json

    logger.info("Fetching preference statistics...")

    orchestrator = WorkflowOrchestrator(config)
    stats = orchestrator.get_statistics()

    print("\nPreference Learning Statistics:")
    print(f"  Total movements: {stats['preferences']['total_movements']}")
    print(f"  Total preferences: {stats['preferences']['total_preferences']}")
    print(f"  High confidence: {stats['preferences']['high_confidence_preferences']}")

    print("\nBooru Cache Statistics:")
    print(f"  Total entries: {stats['booru_cache']['total_entries']}")
    print(f"  Valid entries: {stats['booru_cache']['valid_entries']}")

    return 0


def cmd_export_preferences(config, args):
    """Export preferences to JSON."""
    from src.learning import PreferenceDatabase
    import json

    logger.info(f"Exporting preferences to: {args.output}")

    db_path = config.get('learning', {}).get('database_path', 'data/preferences.db')
    pref_db = PreferenceDatabase(db_path)

    preferences = pref_db.export_preferences()

    with open(args.output, 'w') as f:
        json.dump(preferences, f, indent=2)

    print(f"Exported {len(preferences['preferences'])} preferences to {args.output}")

    return 0


def cmd_reset_preferences(config, args):
    """Reset all preferences."""
    from src.learning import PreferenceDatabase

    logger.warning("Resetting all learned preferences...")

    # Confirm with user
    response = input("Are you sure you want to reset all preferences? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return 0

    db_path = config.get('learning', {}).get('database_path', 'data/preferences.db')
    pref_db = PreferenceDatabase(db_path)

    pref_db.clear_all()
    print("All preferences have been reset.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
