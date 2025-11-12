"""Setup verification script to check dependencies and configuration."""

import sys
import subprocess
from pathlib import Path
import importlib
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class SetupVerifier:
    """Verify system setup and dependencies."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success = []

    def run(self) -> bool:
        """Run all verification checks.

        Returns:
            True if all critical checks pass
        """
        print("="*60)
        print("  Setup Verification")
        print("="*60)
        print()

        # Check Python version
        self._check_python_version()

        # Check required packages
        self._check_required_packages()

        # Check optional packages
        self._check_optional_packages()

        # Check ExifTool
        self._check_exiftool()

        # Check PyTorch
        self._check_pytorch()

        # Check directories
        self._check_directories()

        # Check configuration
        self._check_configuration()

        # Print summary
        self._print_summary()

        return len(self.errors) == 0

    def _check_python_version(self):
        """Check Python version is 3.9+."""
        version = sys.version_info
        if version >= (3, 9):
            self.success.append(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        else:
            self.errors.append(
                f"✗ Python version {version.major}.{version.minor} < 3.9 (required)"
            )

    def _check_required_packages(self):
        """Check required Python packages."""
        required = [
            ('yaml', 'pyyaml'),
            ('PIL', 'pillow'),
            ('requests', 'requests'),
            ('dotenv', 'python-dotenv'),
        ]

        print("Checking required packages...")
        for module_name, package_name in required:
            try:
                importlib.import_module(module_name)
                self.success.append(f"  ✓ {package_name}")
            except ImportError:
                self.errors.append(f"  ✗ {package_name} not installed")

    def _check_optional_packages(self):
        """Check optional Python packages."""
        optional = [
            ('saucenao_api', 'saucenao-api', 'Booru search'),
            ('pybooru', 'pybooru', 'Danbooru integration'),
            ('PicImageSearch', 'PicImageSearch', 'IQDB fallback'),
            ('exiftool', 'pyexiftool', 'XMP writing'),
            ('torch', 'torch', 'Content analysis'),
            ('transformers', 'transformers', 'CLIP classifier'),
            ('jsonschema', 'jsonschema', 'JSON validation'),
            ('tqdm', 'tqdm', 'Progress bars'),
        ]

        print("\nChecking optional packages...")
        for module_name, package_name, purpose in optional:
            try:
                importlib.import_module(module_name)
                self.success.append(f"  ✓ {package_name} ({purpose})")
            except ImportError:
                self.warnings.append(
                    f"  ! {package_name} not installed - {purpose} will be disabled"
                )

    def _check_exiftool(self):
        """Check ExifTool is installed."""
        print("\nChecking ExifTool...")
        try:
            result = subprocess.run(
                ['exiftool', '-ver'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.success.append(f"  ✓ ExifTool {version}")
            else:
                self.warnings.append("  ! ExifTool found but version check failed")
        except FileNotFoundError:
            self.warnings.append(
                "  ! ExifTool not found in PATH - XMP writing will fail"
            )
        except Exception as e:
            self.warnings.append(f"  ! ExifTool check failed: {e}")

    def _check_pytorch(self):
        """Check PyTorch installation and device."""
        print("\nChecking PyTorch...")
        try:
            import torch

            version = torch.__version__
            self.success.append(f"  ✓ PyTorch {version}")

            # Check CUDA availability
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0)
                self.success.append(
                    f"  ✓ CUDA available: {device_count} device(s) - {device_name}"
                )
            else:
                self.warnings.append(
                    "  ! CUDA not available - using CPU (slower)"
                )

        except ImportError:
            self.warnings.append(
                "  ! PyTorch not installed - content analysis disabled"
            )
        except Exception as e:
            self.warnings.append(f"  ! PyTorch check failed: {e}")

    def _check_directories(self):
        """Check required directories exist."""
        print("\nChecking directories...")
        required_dirs = [
            'data/models',
            'data/cache',
            'logs'
        ]

        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists():
                self.success.append(f"  ✓ {dir_path}")
            else:
                self.warnings.append(f"  ! {dir_path} does not exist")
                # Try to create it
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.success.append(f"    ✓ Created {dir_path}")
                except Exception as e:
                    self.errors.append(f"    ✗ Failed to create {dir_path}: {e}")

    def _check_configuration(self):
        """Check configuration file."""
        print("\nChecking configuration...")
        config_path = Path('config/config.yaml')

        if not config_path.exists():
            self.warnings.append(
                "  ! config/config.yaml not found - run setup wizard"
            )
            return

        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Check required sections
            required_sections = [
                'directories',
                'api',
                'content_analysis',
                'workflow',
                'logging'
            ]

            for section in required_sections:
                if section in config:
                    self.success.append(f"  ✓ Section '{section}' present")
                else:
                    self.errors.append(f"  ✗ Section '{section}' missing")

            # Check directories are configured
            if 'directories' in config:
                for key in ['inbox', 'sorted', 'working']:
                    if key in config['directories']:
                        path = Path(config['directories'][key])
                        if path.exists():
                            self.success.append(f"    ✓ {key}: {path}")
                        else:
                            self.warnings.append(
                                f"    ! {key} directory does not exist: {path}"
                            )
                    else:
                        self.errors.append(f"    ✗ {key} not configured")

        except Exception as e:
            self.errors.append(f"  ✗ Failed to load config: {e}")

    def _print_summary(self):
        """Print verification summary."""
        print("\n" + "="*60)
        print("  Verification Summary")
        print("="*60)
        print()

        if self.success:
            print(f"Success: {len(self.success)} items")
            for msg in self.success[:10]:  # Show first 10
                print(msg)
            if len(self.success) > 10:
                print(f"  ... and {len(self.success) - 10} more")
            print()

        if self.warnings:
            print(f"Warnings: {len(self.warnings)} items")
            for msg in self.warnings:
                print(msg)
            print()

        if self.errors:
            print(f"Errors: {len(self.errors)} items")
            for msg in self.errors:
                print(msg)
            print()

        # Final verdict
        if self.errors:
            print("✗ VERIFICATION FAILED - Please fix errors above")
            print()
            print("To install missing packages:")
            print("  pip install -r requirements.txt")
            print()
            return False
        elif self.warnings:
            print("⚠ VERIFICATION PASSED with warnings")
            print("Some features may be disabled. See warnings above.")
            print()
            return True
        else:
            print("✓ VERIFICATION PASSED")
            print("All systems ready!")
            print()
            return True


def main():
    """Run verification."""
    verifier = SetupVerifier()
    success = verifier.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
