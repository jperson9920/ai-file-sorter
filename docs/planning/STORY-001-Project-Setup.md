# STORY-001: Project Setup and Environment Configuration

**Epic:** EPIC-001
**Story Points:** 3
**Priority:** P0 - Blocker
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 1 day

## User Story

As a **developer**, I want to **set up the Python project structure and development environment** so that **I can begin implementing the automated image tagging system with all necessary dependencies installed and configured**.

## Acceptance Criteria

### AC1: Project Structure Created
- [ ] Create Python package structure with proper `__init__.py` files
- [ ] Organize code into logical modules: `booru`, `xmp_writer`, `content_analysis`, `workflow`, `utils`
- [ ] Create directories: `src/`, `tests/`, `config/`, `logs/`, `data/`
- [ ] Add `.gitignore` for Python, virtual environments, and local config files

### AC2: Dependencies Installed
- [ ] Create `requirements.txt` with all required packages
- [ ] Create `requirements-dev.txt` for development tools (pytest, black, pylint)
- [ ] Document Python 3.9+ requirement
- [ ] Verify ExifTool Windows executable is downloadable and accessible

### AC3: Configuration Framework
- [ ] Create `config/config.yaml` template with all required settings
- [ ] Implement configuration loader using PyYAML or ConfigParser
- [ ] Support environment variable overrides for sensitive data (API keys)
- [ ] Validate configuration on startup with helpful error messages

### AC4: Logging Infrastructure
- [ ] Set up Python logging with rotating file handlers
- [ ] Create log levels: DEBUG, INFO, WARNING, ERROR
- [ ] Log to both console and file (`logs/image_tagger.log`)
- [ ] Include timestamps, log levels, and module names in log format

### AC5: Development Tools Configured
- [ ] Add `pytest.ini` for test configuration
- [ ] Add `.pylintrc` for linting rules
- [ ] Create `setup.py` or `pyproject.toml` for package installation
- [ ] Add pre-commit hooks for code formatting (optional)

## Technical Implementation

### Directory Structure
```
ai-file-sorter/
├── src/
│   ├── __init__.py
│   ├── booru/
│   │   ├── __init__.py
│   │   ├── saucenao_client.py
│   │   ├── iqdb_client.py
│   │   ├── danbooru_client.py
│   │   └── tag_normalizer.py
│   ├── xmp_writer/
│   │   ├── __init__.py
│   │   ├── exiftool_wrapper.py
│   │   └── metadata_builder.py
│   ├── content_analysis/
│   │   ├── __init__.py
│   │   ├── clip_classifier.py
│   │   ├── object_detector.py
│   │   └── model_loader.py
│   ├── learning/
│   │   ├── __init__.py
│   │   ├── preference_tracker.py
│   │   └── database.py
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── batch_processor.py
│   │   ├── nas_sync.py
│   │   └── orchestrator.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config_loader.py
│   │   ├── logger.py
│   │   └── file_utils.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── test_booru/
│   ├── test_xmp_writer/
│   ├── test_content_analysis/
│   └── test_workflow/
├── config/
│   ├── config.yaml.example
│   └── README.md
├── data/
│   ├── models/          # Downloaded ML models
│   ├── cache/           # API response cache
│   └── preferences.db   # SQLite database
├── logs/
│   └── .gitkeep
├── docs/
│   └── planning/
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── README.md
└── .gitignore
```

### Requirements.txt Content
```txt
# Core dependencies
pyyaml>=6.0
pillow>=10.0.0
requests>=2.31.0

# Booru integration
saucenao-api>=2.4.0
pybooru>=4.2.2
PicImageSearch>=3.0.0

# XMP writing
pyexiftool>=0.5.6

# ML/AI
torch>=2.0.0
torchvision>=0.15.0
transformers>=4.30.0
numpy>=1.24.0

# Database
jsonschema>=4.17.0

# Utilities
tqdm>=4.65.0
python-dotenv>=1.0.0
```

### Configuration Template (config.yaml.example)
```yaml
# Image Processing Directories
directories:
  inbox: "C:\\ImageProcessing\\Inbox"
  sorted: "C:\\ImageProcessing\\Sorted"
  working: "C:\\ImageProcessing\\Working"
  nas_mount: "Z:\\"  # SMB mount point
  nas_path: "\\\\192.168.1.100\\photos"

# API Configuration (use environment variables for keys)
api:
  saucenao:
    api_key: "${SAUCENAO_API_KEY}"
    rate_limit: 6  # requests per 30 seconds
    min_similarity: 70.0
  danbooru:
    username: "${DANBOORU_USER}"
    api_key: "${DANBOORU_API_KEY}"
  iqdb:
    enabled: true
    min_similarity: 80.0

# Content Analysis Settings
content_analysis:
  enabled: true
  models:
    clip:
      model_name: "openai/clip-vit-base-patch32"
      cache_dir: "data/models"
    faster_rcnn:
      model_name: "fasterrcnn_resnet50_fpn"
      confidence_threshold: 0.7

  classifications:
    - label: "anime style illustration"
      threshold: 0.6
    - label: "realistic photograph"
      threshold: 0.6
    - label: "3D render"
      threshold: 0.5

# XMP Metadata Settings
xmp:
  exiftool_path: "C:\\Tools\\exiftool.exe"  # Auto-detect if in PATH
  sidecar_format: "{filename}.xmp"  # IMG_001.jpg -> IMG_001.jpg.xmp
  fields:
    - "XMP-digiKam:TagsList"
    - "IPTC:Keywords"
    - "XMP-dc:Subject"
  include_rating: true
  include_description: true

# Preference Learning
learning:
  database_path: "data/preferences.db"
  min_confidence: 0.7
  min_samples: 50  # Corrections needed before high confidence

# Workflow Settings
workflow:
  batch_size: 100  # Images per batch
  parallel_workers: 4
  enable_gui_review: true
  auto_approve_high_confidence: false

# NAS Sync Settings
sync:
  enabled: true
  robocopy_options: "/MIR /XO /R:3 /W:5"
  schedule: "manual"  # or "auto" for scheduled

# Logging
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "logs/image_tagger.log"
  max_bytes: 10485760  # 10MB
  backup_count: 5
  console_output: true

# Performance
performance:
  cache_enabled: true
  cache_ttl_hours: 48
  max_cache_size_mb: 500
```

### Logger Setup (utils/logger.py)
```python
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

def setup_logger(config):
    """Initialize logging with file and console handlers."""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/image_tagger.log')

    # Create logs directory if it doesn't exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # File handler with rotation
    max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
    backup_count = log_config.get('backup_count', 5)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    if log_config.get('console_output', True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
```

## Testing Strategy

### Unit Tests
- [ ] Test configuration loader with valid and invalid YAML
- [ ] Test environment variable substitution
- [ ] Test logger initialization and log file creation
- [ ] Test directory structure creation

### Integration Tests
- [ ] Verify all dependencies install correctly on clean Windows 11
- [ ] Test ExifTool can be found and executed
- [ ] Verify configuration loads without errors

## Definition of Done

- [ ] All directory structure created and committed
- [ ] requirements.txt tested on clean Python 3.9+ environment
- [ ] Configuration template documented with comments
- [ ] Logging produces output to both file and console
- [ ] Unit tests pass with 80%+ coverage
- [ ] README.md updated with setup instructions
- [ ] Code reviewed and approved
- [ ] Merged to development branch

## Dependencies

**Depends On:**
- None (foundation story)

**Blocks:**
- STORY-002 (Booru reverse image search)
- STORY-003 (XMP sidecar writer)
- All other implementation stories

## Notes

- ExifTool must be downloaded separately from https://exiftool.org/
- Consider using `python-dotenv` for `.env` file support
- Ensure `.gitignore` excludes API keys and local configuration
- Document Windows-specific path requirements (backslashes, drive letters)

## Risks

- **Low Risk:** Dependency conflicts between packages
  - *Mitigation:* Pin specific versions in requirements.txt

## Related Files

- `/config/config.yaml.example`
- `/src/utils/config_loader.py`
- `/src/utils/logger.py`
- `/requirements.txt`
- `/setup.py`

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
