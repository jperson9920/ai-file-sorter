"""Interactive setup wizard for first-time configuration."""

from pathlib import Path
from typing import Dict, Optional
import yaml
import sys
import os

class SetupWizard:
    """Interactive setup wizard for first-time configuration."""

    def __init__(self):
        self.config = {}

    def run(self) -> Dict:
        """Run interactive setup wizard.

        Returns:
            Configuration dict
        """
        print("="*60)
        print("  Automated Image Tagging System - Setup Wizard")
        print("="*60)
        print("\nThis wizard will help you configure the system.")
        print("Press Ctrl+C at any time to cancel.\n")

        try:
            # Step 1: Directories
            self._setup_directories()

            # Step 2: API Keys
            self._setup_api_keys()

            # Step 3: Content Analysis
            self._setup_content_analysis()

            # Step 4: NAS Sync
            self._setup_nas_sync()

            # Step 5: Advanced Settings
            self._setup_advanced()

            # Step 6: Review and confirm
            self._review_configuration()

            # Step 7: Save configuration
            self._save_configuration()

            print("\n✓ Setup complete!")
            print(f"Configuration saved to: config/config.yaml")
            print("\nNext steps:")
            print("  1. Run 'python -m src.utils.verify_setup' to verify installation")
            print("  2. Run 'python -m src.main --help' to see usage options")
            print("  3. Place images in your inbox directory to start processing")

            return self.config

        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            sys.exit(1)

    def _setup_directories(self):
        """Configure directory paths."""
        print("\n--- Step 1: Directory Configuration ---\n")

        # Inbox directory
        inbox = self._prompt_path(
            "Enter inbox directory (where new images arrive)",
            default="C:\\ImageProcessing\\Inbox",
            must_exist=False
        )

        # Sorted directory
        sorted_dir = self._prompt_path(
            "Enter sorted directory (where categorized images go)",
            default="C:\\ImageProcessing\\Sorted",
            must_exist=False
        )

        # Working directory
        working = self._prompt_path(
            "Enter working directory (for temporary files)",
            default="C:\\ImageProcessing\\Working",
            must_exist=False
        )

        self.config['directories'] = {
            'inbox': str(inbox),
            'sorted': str(sorted_dir),
            'working': str(working),
            'nas_mount': 'Z:\\',
            'nas_path': ''
        }

        # Create directories
        print()
        for path in [inbox, sorted_dir, working]:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {path}")

        # Create data directories
        for data_dir in ['data/models', 'data/cache', 'logs']:
            Path(data_dir).mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {data_dir}")

    def _setup_api_keys(self):
        """Configure API keys."""
        print("\n--- Step 2: API Keys ---\n")

        print("SauceNAO API Key:")
        print("  Get your free API key at: https://saucenao.com/user.php")
        print("  Free tier: 200 searches/day")
        saucenao_key = self._prompt_string(
            "Enter SauceNAO API key (or press Enter to skip)",
            required=False
        )

        print("\nDanbooru API Key:")
        print("  Register at: https://danbooru.donmai.us/")
        print("  Note: Some features require Gold+ account")
        danbooru_user = self._prompt_string(
            "Enter Danbooru username (or press Enter to skip)",
            required=False
        )
        danbooru_key = ""
        if danbooru_user:
            danbooru_key = self._prompt_string(
                "Enter Danbooru API key (or press Enter to skip)",
                required=False
            )

        self.config['api'] = {
            'saucenao': {
                'api_key': saucenao_key or '${SAUCENAO_API_KEY}',
                'rate_limit': 6,
                'min_similarity': 70.0
            },
            'danbooru': {
                'username': danbooru_user or '${DANBOORU_USER}',
                'api_key': danbooru_key or '${DANBOORU_API_KEY}'
            },
            'iqdb': {
                'enabled': True,
                'min_similarity': 80.0
            }
        }

        # Save to .env file
        if saucenao_key or danbooru_key:
            self._save_env_file(saucenao_key, danbooru_user, danbooru_key)

    def _setup_content_analysis(self):
        """Configure content analysis."""
        print("\n--- Step 3: Content Analysis ---\n")

        print("Content analysis uses AI models to classify images.")
        print("This requires ~310MB of disk space and 1-2GB RAM.")
        print("Models will be downloaded on first use.")

        enable = self._prompt_yes_no(
            "Enable content analysis?",
            default=True
        )

        self.config['content_analysis'] = {
            'enabled': enable,
            'models': {
                'clip': {
                    'model_name': 'openai/clip-vit-base-patch32',
                    'cache_dir': 'data/models'
                },
                'faster_rcnn': {
                    'model_name': 'fasterrcnn_resnet50_fpn',
                    'confidence_threshold': 0.7
                }
            },
            'classifications': [
                {'label': 'anime style illustration', 'threshold': 0.6},
                {'label': 'realistic photograph', 'threshold': 0.6},
                {'label': '3D render', 'threshold': 0.5}
            ]
        }

    def _setup_nas_sync(self):
        """Configure NAS sync."""
        print("\n--- Step 4: NAS Sync ---\n")

        print("Sync sorted images to Synology NAS for Immich access.")
        print("Requires Windows and a mapped network drive or UNC path.")

        enable = self._prompt_yes_no(
            "Enable NAS sync?",
            default=False
        )

        if enable:
            nas_path = self._prompt_string(
                "Enter NAS path (UNC like \\\\\\\\192.168.1.100\\\\photos or drive like Z:\\\\)",
                required=True
            )

            self.config['directories']['nas_path'] = nas_path
            self.config['sync'] = {
                'enabled': True,
                'robocopy_options': '/MIR /XO /R:3 /W:5',
                'schedule': 'manual'
            }
        else:
            self.config['sync'] = {
                'enabled': False,
                'robocopy_options': '/MIR /XO /R:3 /W:5',
                'schedule': 'manual'
            }

    def _setup_advanced(self):
        """Configure advanced settings."""
        print("\n--- Step 5: Advanced Settings ---\n")

        batch_size = self._prompt_int(
            "Batch size (images to process at once)",
            default=100,
            min_val=1,
            max_val=1000
        )

        parallel_workers = self._prompt_int(
            "Parallel workers (for concurrent processing)",
            default=4,
            min_val=1,
            max_val=16
        )

        self.config['workflow'] = {
            'batch_size': batch_size,
            'parallel_workers': parallel_workers,
            'enable_gui_review': False,
            'auto_approve_high_confidence': True
        }

        # XMP settings
        self.config['xmp'] = {
            'exiftool_path': '',  # Auto-detect
            'sidecar_format': '{filename}.xmp',
            'fields': [
                'XMP-digiKam:TagsList',
                'IPTC:Keywords',
                'XMP-dc:Subject'
            ],
            'include_rating': self._prompt_yes_no("Include rating in XMP?", default=False),
            'include_description': True
        }

        # Learning settings
        self.config['learning'] = {
            'database_path': 'data/preferences.db',
            'min_confidence': 0.7,
            'min_samples': 50
        }

        # Logging
        log_level = self._prompt_choice(
            "Log level",
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO'
        )

        self.config['logging'] = {
            'level': log_level,
            'file': 'logs/image_tagger.log',
            'max_bytes': 10485760,
            'backup_count': 5,
            'console_output': True
        }

        # Performance
        self.config['performance'] = {
            'cache_enabled': True,
            'cache_ttl_hours': 48,
            'max_cache_size_mb': 500
        }

    def _review_configuration(self):
        """Review configuration before saving."""
        print("\n--- Configuration Review ---\n")

        print(f"Directories:")
        print(f"  Inbox:   {self.config['directories']['inbox']}")
        print(f"  Sorted:  {self.config['directories']['sorted']}")
        print(f"  Working: {self.config['directories']['working']}")

        print(f"\nAPI Keys:")
        print(f"  SauceNAO: {'Set' if '${' not in str(self.config['api']['saucenao']['api_key']) else 'Not set'}")
        print(f"  Danbooru: {'Set' if '${' not in str(self.config['api']['danbooru']['api_key']) else 'Not set'}")

        print(f"\nContent Analysis: {'Enabled' if self.config['content_analysis']['enabled'] else 'Disabled'}")
        print(f"NAS Sync: {'Enabled' if self.config.get('sync', {}).get('enabled') else 'Disabled'}")

        print(f"\nWorkflow:")
        print(f"  Batch size: {self.config['workflow']['batch_size']}")
        print(f"  Workers: {self.config['workflow']['parallel_workers']}")

        if not self._prompt_yes_no("\nSave this configuration?", default=True):
            print("Configuration not saved. Exiting.")
            sys.exit(0)

    def _save_configuration(self):
        """Save configuration to file."""
        config_path = Path('config/config.yaml')
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

    def _save_env_file(self, saucenao_key: str, danbooru_user: str, danbooru_key: str):
        """Save API keys to .env file."""
        env_path = Path('.env')

        with open(env_path, 'w') as f:
            if saucenao_key:
                f.write(f"SAUCENAO_API_KEY={saucenao_key}\n")
            if danbooru_user:
                f.write(f"DANBOORU_USER={danbooru_user}\n")
            if danbooru_key:
                f.write(f"DANBOORU_API_KEY={danbooru_key}\n")

        print(f"\n  ✓ API keys saved to: {env_path}")

    # Helper methods
    def _prompt_string(self, prompt: str, default: str = "", required: bool = True) -> str:
        """Prompt for string input."""
        while True:
            if default:
                value = input(f"{prompt} [{default}]: ").strip()
                if not value:
                    value = default
            else:
                value = input(f"{prompt}: ").strip()

            if value or not required:
                return value
            print("  Error: This field is required.")

    def _prompt_path(self, prompt: str, default: str = "", must_exist: bool = False) -> Path:
        """Prompt for path input."""
        while True:
            path_str = self._prompt_string(prompt, default, required=True)
            path = Path(path_str)

            if must_exist and not path.exists():
                print(f"  Error: Path does not exist: {path}")
                continue

            return path

    def _prompt_int(self, prompt: str, default: int, min_val: int = None, max_val: int = None) -> int:
        """Prompt for integer input."""
        while True:
            value = input(f"{prompt} [{default}]: ").strip()
            if not value:
                return default

            try:
                int_val = int(value)
                if min_val is not None and int_val < min_val:
                    print(f"  Error: Value must be >= {min_val}")
                    continue
                if max_val is not None and int_val > max_val:
                    print(f"  Error: Value must be <= {max_val}")
                    continue
                return int_val
            except ValueError:
                print("  Error: Please enter a valid number.")

    def _prompt_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Prompt for yes/no input."""
        default_str = "Y/n" if default else "y/N"
        while True:
            value = input(f"{prompt} [{default_str}]: ").strip().lower()

            if not value:
                return default

            if value in ['y', 'yes']:
                return True
            elif value in ['n', 'no']:
                return False
            else:
                print("  Error: Please enter 'y' or 'n'.")

    def _prompt_choice(self, prompt: str, choices: list, default: str) -> str:
        """Prompt for choice from list."""
        choices_str = "/".join(choices)
        while True:
            value = input(f"{prompt} [{choices_str}] [{default}]: ").strip().upper()

            if not value:
                return default

            if value in choices:
                return value
            else:
                print(f"  Error: Please choose from: {choices_str}")


def main():
    """Run setup wizard."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == '__main__':
    main()
