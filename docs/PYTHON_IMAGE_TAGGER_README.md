# Automated Image Tagging System

Complete Python-based automated image tagging system for Windows 11 that uses reverse image search (SauceNAO/Danbooru) and AI models (CLIP + Faster R-CNN) to automatically tag anime images with human-curated metadata.

## Features

- 🔍 **Reverse Image Search**: SauceNAO + IQDB + Danbooru integration for finding existing tags
- 🤖 **AI Content Analysis**: CLIP for style classification, Faster R-CNN for person detection
- 📝 **XMP Sidecar Writing**: Non-destructive metadata tagging for Immich compatibility
- 🧠 **Preference Learning**: SQLite-based system that learns from your tagging behavior
- 🔄 **NAS Sync**: Robocopy integration for Windows-to-Synology sync
- ⚡ **High Performance**: Process 1,000 images in ~45 minutes
- 🔒 **Privacy-Focused**: All processing happens locally (except reverse search APIs)

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/jperson9920/ai-file-sorter.git
cd ai-file-sorter

# Install Python dependencies
pip install -r requirements.txt

# Install ExifTool (Windows)
# Download from: https://exiftool.org/
# Add to PATH or specify path in config
```

### 2. Setup

```bash
# Run interactive setup wizard
python -m src.utils.setup_wizard

# Or manually copy and edit config
cp config/config.yaml.example config/config.yaml
cp .env.example .env
# Edit config/config.yaml and .env with your settings
```

### 3. Verify Installation

```bash
# Check dependencies and configuration
python -m src.utils.verify_setup
```

### 4. Process Images

```bash
# Process all images in inbox
python -m src.main process

# Skip images that already have XMP sidecars
python -m src.main process --skip-existing

# Sync to NAS
python -m src.main sync

# View statistics
python -m src.main stats
```

## System Architecture

```
┌─────────────┐
│   Inbox     │  New images arrive here
│   Images    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        Reverse Image Search              │
│  SauceNAO → IQDB → Danbooru             │
│  (70-90% match rate for anime)          │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        AI Content Analysis               │
│  • CLIP: Style classification            │
│  • Faster R-CNN: Person detection        │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        Metadata Building                 │
│  Combine booru tags + AI analysis        │
│  Normalize to human-readable format      │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        XMP Sidecar Writing               │
│  • XMP-digiKam:TagsList (Immich)        │
│  • IPTC:Keywords                         │
│  • XMP-dc:Subject                        │
│  • Rating, Description, Source URL       │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        Preference Learning               │
│  Track user behavior and improve         │
│  suggestions over time                   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│        NAS Sync (Optional)               │
│  Robocopy to Synology for Immich         │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Immich    │  Searchable images with metadata
│  On NAS     │
└─────────────┘
```

## Performance Targets

| Component | Target | Status |
|-----------|--------|--------|
| Booru Search | 6 req/30s | ✅ Rate limited |
| XMP Writing | 1,000 in 60s | ✅ stay_open mode |
| AI Analysis | 1,000 in 5min | ✅ Batch processing |
| JSON Validation | 1,000 in 2-3s | ✅ 8 workers |
| **End-to-End** | **1,000 in 45min** | ✅ **Complete** |

## Configuration

See `config/config.yaml.example` for complete configuration reference.

### Key Settings

```yaml
directories:
  inbox: "C:\\ImageProcessing\\Inbox"
  sorted: "C:\\ImageProcessing\\Sorted"
  nas_path: "\\\\192.168.1.100\\photos"

api:
  saucenao:
    api_key: "${SAUCENAO_API_KEY}"  # Get from saucenao.com
    rate_limit: 6  # Free tier: 200/day
  danbooru:
    username: "${DANBOORU_USER}"
    api_key: "${DANBOORU_API_KEY}"

content_analysis:
  enabled: true
  models:
    clip:
      model_name: "openai/clip-vit-base-patch32"  # 150MB
    faster_rcnn:
      confidence_threshold: 0.7

workflow:
  batch_size: 100
  parallel_workers: 4
```

## Usage Examples

### Basic Workflow

```bash
# 1. Place images in inbox
cp /path/to/images/* C:\ImageProcessing\Inbox\

# 2. Process images
python -m src.main process

# 3. Review XMP sidecars (created alongside images)
# image.jpg.xmp contains all tags

# 4. Sync to NAS (optional)
python -m src.main sync
```

### Advanced Usage

```python
# Use components programmatically
from src.workflow import WorkflowOrchestrator
from src.utils.config_loader import ConfigLoader
import asyncio

# Load config
config = ConfigLoader('config/config.yaml').load()

# Initialize orchestrator
orchestrator = WorkflowOrchestrator(config)

# Process single image
async def process_one():
    result = await orchestrator.process_image(
        Path('test.jpg'),
        skip_existing=False
    )
    print(result)

asyncio.run(process_one())

# Get statistics
stats = orchestrator.get_statistics()
print(f"Cache entries: {stats['booru_cache']['total_entries']}")
print(f"Learned preferences: {stats['preferences']['total_preferences']}")
```

### Preference Management

```bash
# Export learned preferences
python -m src.main export-preferences preferences.json

# Reset all learned preferences
python -m src.main reset-preferences

# View statistics
python -m src.main stats
```

## API Keys

### SauceNAO
1. Register at [saucenao.com](https://saucenao.com/user.php)
2. Get API key from user settings
3. Free tier: 200 searches/day
4. Paid tiers available for higher limits

### Danbooru
1. Register at [danbooru.donmai.us](https://danbooru.donmai.us/)
2. Generate API key in profile settings
3. Free tier: Basic access
4. Gold+ account: Unlimited tag access

Store keys in `.env` file:
```bash
SAUCENAO_API_KEY=your_key_here
DANBOORU_USER=your_username
DANBOORU_API_KEY=your_api_key
```

## ML Models

Models are automatically downloaded on first use:

- **CLIP ViT-B/32**: ~150MB, style classification
- **Faster R-CNN ResNet50**: ~160MB, object detection
- Total: ~310MB disk space, 1-2GB RAM

Models are cached in `data/models/` directory.

## Immich Integration

### Setup Immich on Synology NAS

1. Install Container Manager (DSM 7.x)
2. Create directories:
   ```bash
   mkdir -p /volume1/docker/immich-app/{postgres,library}
   mkdir -p /volume1/photos/master
   ```

3. Deploy Immich with docker-compose
4. Mount photos as external library (read-only)
5. XMP sidecars are automatically read by Immich

### XMP Tag Format

Tags are written in Immich-compatible format:
```xml
<XMP-digiKam:TagsList>Series/Naruto</XMP-digiKam:TagsList>
<XMP-digiKam:TagsList>Series/Naruto/Hinata Hyuga</XMP-digiKam:TagsList>
<XMP-digiKam:TagsList>Blue Eyes</XMP-digiKam:TagsList>
<IPTC:Keywords>Blue Eyes</IPTC:Keywords>
<XMP-dc:Description>Matched via Danbooru (85.5% similarity)</XMP-dc:Description>
```

## Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests
pytest -m e2e           # End-to-end tests
pytest -m benchmark     # Performance benchmarks

# Run with coverage
pytest --cov=src --cov-report=html

# Skip slow tests
pytest -m "not slow"
```

## Troubleshooting

### ExifTool Not Found
```bash
# Windows: Download from exiftool.org
# Add to PATH or specify in config:
xmp:
  exiftool_path: "C:\\Tools\\exiftool.exe"
```

### CUDA Not Available
```
# CPU mode is supported (slower but works)
# To enable GPU:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Rate Limit Errors
```
# SauceNAO rate limits: 6 requests per 30 seconds
# System automatically handles rate limiting
# Consider paid tier for higher limits
```

### Models Not Downloading
```bash
# Manual download:
python -c "from transformers import CLIPModel; CLIPModel.from_pretrained('openai/clip-vit-base-patch32')"
```

## Project Structure

```
ai-file-sorter/
├── src/
│   ├── booru/              # Reverse image search
│   │   ├── saucenao_client.py
│   │   ├── iqdb_client.py
│   │   ├── danbooru_client.py
│   │   ├── tag_normalizer.py
│   │   └── booru_searcher.py
│   ├── content_analysis/   # AI classification
│   │   ├── clip_classifier.py
│   │   ├── object_detector.py
│   │   └── content_analyzer.py
│   ├── xmp_writer/         # XMP metadata
│   │   ├── exiftool_wrapper.py
│   │   └── metadata_builder.py
│   ├── learning/           # Preference tracking
│   │   └── preference_database.py
│   ├── workflow/           # Orchestration
│   │   ├── orchestrator.py
│   │   ├── nas_sync.py
│   │   └── json_validator.py
│   ├── utils/              # Utilities
│   │   ├── config_loader.py
│   │   ├── logger.py
│   │   ├── setup_wizard.py
│   │   └── verify_setup.py
│   └── main.py             # CLI entry point
├── tests/                  # Test suite
├── config/                 # Configuration
├── data/                   # Models, cache, DB
└── docs/                   # Documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run test suite: `pytest`
5. Submit pull request

## License

See LICENSE file in repository root.

## Credits

- **SauceNAO**: Reverse image search API
- **Danbooru**: Booru tag database
- **CLIP**: OpenAI's Contrastive Language-Image Pre-training
- **PyTorch/torchvision**: ML framework
- **ExifTool**: Metadata manipulation
- **Immich**: Self-hosted photo management

## Support

- Documentation: See `docs/` directory
- Issues: GitHub issue tracker
- API docs: Component docstrings

---

Built with ❤️ for the anime image organization community
