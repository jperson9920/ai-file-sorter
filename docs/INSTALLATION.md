# Installation Guide

Complete installation instructions for the Automated Image Tagging System on Windows 11.

## Prerequisites

- Windows 11 (or Windows 10)
- Python 3.9 or higher
- 4GB RAM minimum (8GB recommended for AI features)
- 2GB free disk space (for models and cache)
- Internet connection (for initial setup and API access)

## Step-by-Step Installation

### 1. Install Python

1. Download Python 3.9+ from [python.org](https://www.python.org/downloads/)
2. Run installer
3. **Important**: Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
   ```cmd
   python --version
   ```
   Should show Python 3.9.x or higher

### 2. Install Git (Optional)

If you want to clone the repository:
1. Download Git from [git-scm.com](https://git-scm.com/downloads)
2. Run installer with default settings
3. Verify:
   ```cmd
   git --version
   ```

Alternatively, download the repository as a ZIP file from GitHub.

### 3. Get the Code

**Option A: Using Git**
```cmd
git clone https://github.com/jperson9920/ai-file-sorter.git
cd ai-file-sorter
```

**Option B: Download ZIP**
1. Download ZIP from GitHub
2. Extract to desired location
3. Open Command Prompt in that directory

### 4. Install Python Dependencies

```cmd
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

This will install:
- PyYAML (configuration)
- Pillow (image processing)
- requests (HTTP client)
- saucenao-api (reverse search)
- pybooru (Danbooru API)
- PicImageSearch (IQDB fallback)
- pyexiftool (XMP writing)
- torch & torchvision (AI models)
- transformers (CLIP)
- python-dotenv (environment variables)
- tqdm (progress bars)
- jsonschema (validation)

**Installation time**: 5-10 minutes depending on internet speed

### 5. Install ExifTool

ExifTool is required for XMP sidecar writing.

1. Download Windows Executable from [exiftool.org](https://exiftool.org/)
2. Extract `exiftool(-k).exe`
3. Rename to `exiftool.exe`
4. Place in one of these locations:
   - Same directory as the Python project
   - `C:\Windows\System32\`
   - Add to PATH environment variable
5. Verify installation:
   ```cmd
   exiftool -ver
   ```
   Should show version number (e.g., 12.50)

### 6. Run Setup Wizard

The setup wizard will guide you through configuration:

```cmd
python -m src.utils.setup_wizard
```

You'll be prompted for:
- **Directories**: Where to store images
- **API Keys**: SauceNAO and Danbooru credentials
- **Content Analysis**: Enable/disable AI features
- **NAS Sync**: Configure Synology sync
- **Advanced Settings**: Batch size, workers, etc.

### 7. Obtain API Keys (Optional but Recommended)

#### SauceNAO API Key

1. Go to [saucenao.com](https://saucenao.com/)
2. Create account (free)
3. Navigate to [User Settings](https://saucenao.com/user.php)
4. Copy your API key
5. **Free Tier Limits**:
   - 100 searches/day without key
   - 200 searches/day with key
   - 6 searches per 30 seconds

#### Danbooru API Key

1. Go to [danbooru.donmai.us](https://danbooru.donmai.us/)
2. Create account (free)
3. Go to Profile → API Keys
4. Generate new API key
5. **Access Levels**:
   - Free: Basic tag access
   - Gold+ ($20/year): Unlimited tags, advanced features

**Note**: You can skip API keys during setup and add them later to `.env` file.

### 8. Configure API Keys

Create `.env` file in project root:

```bash
SAUCENAO_API_KEY=your_saucenao_key_here
DANBOORU_USER=your_username
DANBOORU_API_KEY=your_danbooru_key_here
```

Alternatively, the setup wizard can create this file for you.

### 9. Verify Installation

Run the verification script:

```cmd
python -m src.utils.verify_setup
```

This will check:
- ✓ Python version (3.9+)
- ✓ Required packages installed
- ✓ Optional packages installed
- ✓ ExifTool available
- ✓ PyTorch and CUDA status
- ✓ Directories exist
- ✓ Configuration valid

**Expected output**:
```
============================================================
  Setup Verification
============================================================

Checking required packages...
  ✓ pyyaml
  ✓ pillow
  ✓ requests
  ✓ python-dotenv

Checking optional packages...
  ✓ saucenao-api (Booru search)
  ✓ pybooru (Danbooru integration)
  ✓ torch (Content analysis)
  ✓ transformers (CLIP classifier)

Checking ExifTool...
  ✓ ExifTool 12.50

Checking PyTorch...
  ✓ PyTorch 2.0.1
  ! CUDA not available - using CPU (slower)

============================================================
  Verification Summary
============================================================

✓ VERIFICATION PASSED with warnings
Some features may be disabled. See warnings above.
```

### 10. Test Run

Process a few test images:

```cmd
# Copy test images to inbox
mkdir C:\ImageProcessing\Inbox
copy sample_images\*.jpg C:\ImageProcessing\Inbox\

# Process images
python -m src.main process

# Check results
dir C:\ImageProcessing\Inbox\*.xmp
```

You should see `.xmp` files created alongside your images.

## GPU Support (Optional)

For faster AI processing, install PyTorch with CUDA support:

### Check GPU Compatibility

1. Open Device Manager
2. Check Display Adapters
3. If you have NVIDIA GPU, note the model

### Install CUDA Toolkit

1. Download from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads)
2. Install CUDA Toolkit 11.8 or 12.1
3. Restart computer

### Install PyTorch with CUDA

```cmd
# Uninstall CPU version
pip uninstall torch torchvision

# Install CUDA version (for CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Or for CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Verify GPU Support

```cmd
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

Should print: `CUDA available: True`

**Performance improvement**: ~10x faster AI processing with GPU

## Troubleshooting

### Python Not Found

```cmd
# Add Python to PATH manually
# Control Panel → System → Advanced → Environment Variables
# Add to PATH: C:\Users\YourName\AppData\Local\Programs\Python\Python39
```

### pip Install Fails

```cmd
# Upgrade pip
python -m pip install --upgrade pip

# If behind proxy
pip install -r requirements.txt --proxy http://proxy:port

# If SSL errors
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### ExifTool Not Found

```cmd
# Check if in PATH
where exiftool

# If not found, specify path in config.yaml
xmp:
  exiftool_path: "C:\\Path\\To\\exiftool.exe"
```

### PyTorch Installation Issues

```cmd
# Use specific version
pip install torch==2.0.1 torchvision==0.15.2

# Or install CPU-only (smaller, no CUDA required)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Memory Errors

If you encounter memory errors:
1. Reduce batch_size in config.yaml (default: 100 → 50 or 25)
2. Reduce parallel_workers (default: 4 → 2)
3. Disable content_analysis if not needed

### Permission Errors

Run Command Prompt as Administrator:
1. Right-click Command Prompt
2. Select "Run as administrator"
3. Navigate to project directory
4. Run installation commands

## Updating

To update to latest version:

```cmd
# Using Git
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run verification
python -m src.utils.verify_setup
```

## Uninstallation

To remove the system:

```cmd
# Deactivate virtual environment
deactivate

# Delete project directory
# Delete data directory (if you want to remove cached models)
rmdir /S data

# Optional: Uninstall Python packages
pip uninstall -r requirements.txt -y
```

## Next Steps

After successful installation:

1. Read [User Guide](USER_GUIDE.md) for usage instructions
2. Review [Configuration](../config/config.yaml.example) options
3. See [Architecture](ARCHITECTURE.md) for technical details
4. Check [FAQ](FAQ.md) for common questions

---

**Installation Complete!** 🎉

You're ready to start tagging images automatically.
