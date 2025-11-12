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
    logger.info("Starting image processing workflow...")

    # This will be implemented in STORY-008
    print("Process command not yet implemented.")
    print("This will be available after STORY-008: Workflow Orchestration")

    return 0


def cmd_sync(config, args):
    """Sync to NAS."""
    logger.info("Starting NAS sync...")

    # This will be implemented in STORY-006
    print("Sync command not yet implemented.")
    print("This will be available after STORY-006: NAS Sync")

    return 0


def cmd_stats(config, args):
    """Show preference statistics."""
    logger.info("Fetching preference statistics...")

    # This will be implemented in STORY-005
    print("Stats command not yet implemented.")
    print("This will be available after STORY-005: Preference Learning")

    return 0


def cmd_export_preferences(config, args):
    """Export preferences to JSON."""
    logger.info(f"Exporting preferences to: {args.output}")

    # This will be implemented in STORY-005
    print("Export preferences command not yet implemented.")
    print("This will be available after STORY-005: Preference Learning")

    return 0


def cmd_reset_preferences(config, args):
    """Reset all preferences."""
    logger.warning("Resetting all learned preferences...")

    # This will be implemented in STORY-005
    print("Reset preferences command not yet implemented.")
    print("This will be available after STORY-005: Preference Learning")

    return 0


if __name__ == '__main__':
    sys.exit(main())
