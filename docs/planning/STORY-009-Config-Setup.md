# STORY-009: Configuration Management and Setup Scripts

**Epic:** EPIC-001
**Story Points:** 3
**Priority:** P2 - Medium
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 2 days

## User Story

As a **user**, I want to **easily configure and set up the system with guided scripts** so that **I can get started quickly without manually editing configuration files or understanding complex setup steps**.

## Acceptance Criteria

### AC1: Setup Wizard
- [ ] Interactive CLI setup wizard for first-time configuration
- [ ] Prompt for all required settings (directories, API keys, etc.)
- [ ] Validate inputs (paths exist, API keys format correct)
- [ ] Generate `config/config.yaml` from user responses
- [ ] Securely store API keys in environment variables or keyring

### AC2: Directory Structure Creation
- [ ] Automatically create required directories:
  - `C:\ImageProcessing\Inbox`
  - `C:\ImageProcessing\Sorted`
  - `C:\ImageProcessing\Working`
  - `data/models`
  - `data/cache`
  - `logs`
- [ ] Set proper permissions on directories
- [ ] Verify write access to all directories

### AC3: Dependency Verification
- [ ] Check Python version (3.9+)
- [ ] Verify all required packages installed
- [ ] Check for ExifTool executable
- [ ] Test PyTorch installation and device (CPU/GPU)
- [ ] Verify network connectivity
- [ ] Generate comprehensive diagnostic report

### AC4: API Key Management
- [ ] Support `.env` file for API keys
- [ ] Support Windows environment variables
- [ ] Support secure keyring storage (optional)
- [ ] Validate API keys by testing connection
- [ ] Warn about free tier rate limits

### AC5: Configuration Validation
- [ ] Validate configuration file syntax (YAML parsing)
- [ ] Check all required fields present
- [ ] Validate field types and ranges
- [ ] Check directory paths exist and are writable
- [ ] Verify API keys are set (not placeholder values)
- [ ] Generate warnings for non-optimal settings

### AC6: Update Scripts
- [ ] Script to download/update models
- [ ] Script to update dependencies (`pip install -U -r requirements.txt`)
- [ ] Script to backup configuration and databases
- [ ] Script to reset/clean working directories

## Technical Implementation

### Setup Wizard

```python
# src/utils/setup_wizard.py
from pathlib import Path
from typing import Dict, Optional
import yaml
import logging
import sys
import os

logger = logging.getLogger(__name__)

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
        print("Image Tagging System - Setup Wizard")
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
            'working': str(working)
        }

        # Create directories
        for path in [inbox, sorted_dir, working]:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {path}")

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
        danbooru_key = self._prompt_string(
            "Enter Danbooru API key (or press Enter to skip)",
            required=False
        ) if danbooru_user else ""

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

        enable = self._prompt_yes_no(
            "Enable NAS sync?",
            default=False
        )

        if enable:
            nas_path = self._prompt_string(
                "Enter NAS path (UNC path like \\\\192.168.1.100\\photos or drive letter like Z:\\)",
                required=True
            )

            self.config['directories']['nas_path'] = nas_path
            self.config['sync'] = {
                'enabled': True,
                'robocopy_options': '/MIR /XO /R:3 /W:5',
                'schedule': 'manual'
            }
        else:
            self.config['directories']['nas_path'] = ''
            self.config['sync'] = {'enabled': False}

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

        enable_gui_review = self._prompt_yes_no(
            "Enable GUI review for tag approval?",
            default=False
        )

        self.config['workflow'] = {
            'batch_size': batch_size,
            'parallel_workers': parallel_workers,
            'enable_gui_review': enable_gui_review,
            'auto_approve_high_confidence': not enable_gui_review
        }

        # XMP settings
        exiftool_path = self._prompt_path(
            "Enter ExifTool path (or press Enter for auto-detect)",
            default="",
            must_exist=False,
            allow_empty=True
        )

        self.config['xmp'] = {
            'exiftool_path': str(exiftool_path) if exiftool_path else '',
            'sidecar_format': '{filename}.xmp',
            'fields': [
                'XMP-digiKam:TagsList',
                'IPTC:Keywords',
                'XMP-dc:Subject'
            ],
            'include_rating': True,
            'include_description': True
        }

        # Logging
        self.config['logging'] = {
            'level': 'INFO',
            'file': 'logs/image_tagger.log',
            'max_bytes': 10485760,
            'backup_count': 5,
            'console_output': True
        }

        # Learning
        self.config['learning'] = {
            'database_path': 'data/preferences.db',
            'min_confidence': 0.7,
            'min_samples': 50
        }

        # Performance
        self.config['performance'] = {
            'cache_enabled': True,
            'cache_ttl_hours': 48,
            'max_cache_size_mb': 500
        }

    def _review_configuration(self):
        """Display configuration for user review."""
        print("\n--- Configuration Summary ---\n")

        print(f"Inbox directory:     {self.config['directories']['inbox']}")
        print(f"Sorted directory:    {self.config['directories']['sorted']}")
        print(f"Working directory:   {self.config['directories']['working']}")
        print(f"")
        print(f"SauceNAO API:        {'Configured' if '${' not in self.config['api']['saucenao']['api_key'] else 'Not configured'}")
        print(f"Danbooru API:        {'Configured' if '${' not in self.config['api']['danbooru']['api_key'] else 'Not configured'}")
        print(f"")
        print(f"Content Analysis:    {'Enabled' if self.config['content_analysis']['enabled'] else 'Disabled'}")
        print(f"NAS Sync:            {'Enabled' if self.config['sync']['enabled'] else 'Disabled'}")
        print(f"")
        print(f"Batch size:          {self.config['workflow']['batch_size']}")
        print(f"GUI Review:          {'Enabled' if self.config['workflow']['enable_gui_review'] else 'Disabled'}")

        print("\n")
        if not self._prompt_yes_no("Is this configuration correct?", default=True):
            print("Please restart the setup wizard.")
            sys.exit(0)

    def _save_configuration(self):
        """Save configuration to YAML file."""
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)

        config_path = config_dir / 'config.yaml'

        with open(config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

    def _save_env_file(self, saucenao_key: str, danbooru_user: str, danbooru_key: str):
        """Save API keys to .env file."""
        env_path = Path('.env')

        with open(env_path, 'w') as f:
            if saucenao_key:
                f.write(f"SAUCENAO_API_KEY={saucenao_key}\n")
            if danbooru_key:
                f.write(f"DANBOORU_USER={danbooru_user}\n")
                f.write(f"DANBOORU_API_KEY={danbooru_key}\n")

        print(f"  ✓ API keys saved to .env file")

    # Helper methods
    def _prompt_string(self, prompt: str, required: bool = True) -> str:
        """Prompt for string input."""
        while True:
            value = input(f"{prompt}: ").strip()
            if value or not required:
                return value
            print("  ✗ This field is required.")

    def _prompt_path(
        self,
        prompt: str,
        default: str = "",
        must_exist: bool = False,
        allow_empty: bool = False
    ) -> Path:
        """Prompt for path input."""
        while True:
            if default:
                value = input(f"{prompt} [{default}]: ").strip() or default
            else:
                value = input(f"{prompt}: ").strip()

            if not value and allow_empty:
                return Path()

            path = Path(value)

            if must_exist and not path.exists():
                print(f"  ✗ Path does not exist: {path}")
                continue

            return path

    def _prompt_int(
        self,
        prompt: str,
        default: int,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None
    ) -> int:
        """Prompt for integer input."""
        while True:
            value = input(f"{prompt} [{default}]: ").strip() or str(default)

            try:
                int_val = int(value)

                if min_val is not None and int_val < min_val:
                    print(f"  ✗ Value must be >= {min_val}")
                    continue

                if max_val is not None and int_val > max_val:
                    print(f"  ✗ Value must be <= {max_val}")
                    continue

                return int_val

            except ValueError:
                print(f"  ✗ Invalid number: {value}")

    def _prompt_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Prompt for yes/no input."""
        default_str = "Y/n" if default else "y/N"
        value = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not value:
            return default

        return value in ['y', 'yes']


def main():
    """Run setup wizard."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == '__main__':
    main()
```

### Verification Script

```python
# src/utils/verify_setup.py
import sys
from pathlib import Path
import logging
import subprocess

logger = logging.getLogger(__name__)

def verify_python_version() -> bool:
    """Verify Python version is 3.9+."""
    version = sys.version_info
    if version >= (3, 9):
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} (requires 3.9+)")
        return False

def verify_dependencies() -> bool:
    """Verify all required packages are installed."""
    required = [
        'yaml', 'PIL', 'torch', 'transformers', 'exiftool',
        'jsonschema', 'tqdm', 'requests'
    ]

    all_ok = True
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (not installed)")
            all_ok = False

    return all_ok

def verify_exiftool() -> bool:
    """Verify ExifTool is available."""
    try:
        result = subprocess.run(
            ['exiftool', '-ver'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ ExifTool {version}")
            return True
    except FileNotFoundError:
        pass

    print("✗ ExifTool not found in PATH")
    print("  Download from: https://exiftool.org/")
    return False

def verify_pytorch() -> bool:
    """Verify PyTorch installation."""
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        print(f"  Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
        return True
    except ImportError:
        print("✗ PyTorch not installed")
        return False

def verify_directories() -> bool:
    """Verify required directories exist."""
    required_dirs = [
        'config',
        'data/models',
        'data/cache',
        'logs'
    ]

    all_ok = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ (missing)")
            all_ok = False

    return all_ok

def main():
    """Run all verification checks."""
    print("="*60)
    print("Setup Verification")
    print("="*60)

    checks = [
        ("Python Version", verify_python_version),
        ("Dependencies", verify_dependencies),
        ("ExifTool", verify_exiftool),
        ("PyTorch", verify_pytorch),
        ("Directories", verify_directories)
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        result = check_func()
        results.append((name, result))

    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)

    all_passed = all(result for _, result in results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    print("="*60)

    if all_passed:
        print("\n✓ All checks passed! System is ready to use.")
        sys.exit(0)
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Testing Strategy

### Unit Tests
- [ ] Test configuration validation
- [ ] Test directory creation
- [ ] Test YAML parsing and generation

### Integration Tests
- [ ] Run setup wizard with test inputs
- [ ] Verify generated configuration is valid
- [ ] Test verification script detects issues

### Manual Testing
- [ ] Run setup wizard on clean Windows 11 system
- [ ] Verify all directories created correctly
- [ ] Verify .env file created securely
- [ ] Run verification script and confirm all checks pass

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Setup wizard guides user through configuration
- [ ] Verification script detects missing dependencies
- [ ] Configuration file generated correctly
- [ ] Unit tests pass
- [ ] Manual test on clean system succeeds
- [ ] Documentation updated with setup instructions
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-001 (Project structure)

**Blocks:**
- All implementation stories (need configuration)

## Notes

- Setup wizard should be user-friendly for non-technical users
- Consider adding GUI setup wizard in future
- Verification script useful for troubleshooting

## Risks

- **Low Risk:** Windows path handling edge cases
  - *Mitigation:* Thorough testing on Windows 11

## Related Files

- `/src/utils/setup_wizard.py`
- `/src/utils/verify_setup.py`
- `/config/config.yaml` (generated)
- `/.env` (generated)

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
