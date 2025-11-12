# STORY-011: Documentation and User Guide

**Epic:** EPIC-001
**Story Points:** 3
**Priority:** P2 - Medium
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 2 days

## User Story

As a **user**, I want **comprehensive documentation and guides** so that **I can successfully install, configure, and use the system without extensive technical knowledge**.

## Acceptance Criteria

### AC1: README.md
- [ ] Project overview and key features
- [ ] Quick start guide (5-minute setup)
- [ ] Installation instructions for Windows 11
- [ ] Basic usage examples
- [ ] Links to detailed documentation
- [ ] Screenshots/GIFs of system in action

### AC2: Installation Guide
- [ ] System requirements (Python version, RAM, disk space)
- [ ] Step-by-step installation instructions
- [ ] Dependency installation (pip, ExifTool)
- [ ] Configuration setup
- [ ] Verification steps
- [ ] Troubleshooting common installation issues

### AC3: User Guide
- [ ] How to configure the system (directories, API keys)
- [ ] How to process images (batch workflow)
- [ ] How to review and approve tags
- [ ] How to train preferences
- [ ] How to sync to NAS
- [ ] How to use uma.json validator
- [ ] Advanced configuration options

### AC4: API Integration Guide
- [ ] How to get SauceNAO API key
- [ ] How to get Danbooru account and API key
- [ ] Rate limits and best practices
- [ ] Cost estimation for paid tiers

### AC5: Architecture Documentation
- [ ] System architecture diagram
- [ ] Component descriptions
- [ ] Data flow diagrams
- [ ] Database schema documentation
- [ ] XMP metadata format specification

### AC6: Developer Documentation
- [ ] Code structure overview
- [ ] How to extend the system
- [ ] How to add new classification rules
- [ ] How to customize categorization logic
- [ ] How to contribute (CONTRIBUTING.md)

### AC7: FAQ and Troubleshooting
- [ ] Common issues and solutions
- [ ] Performance optimization tips
- [ ] Error message explanations
- [ ] How to report bugs
- [ ] How to request features

## Technical Implementation

### Documentation Structure

```
docs/
├── README.md                          # Main project README
├── INSTALLATION.md                    # Detailed installation guide
├── USER_GUIDE.md                      # Complete user guide
├── CONFIGURATION.md                   # Configuration reference
├── API_INTEGRATION.md                 # API setup and usage
├── ARCHITECTURE.md                    # Technical architecture
├── DEVELOPER_GUIDE.md                 # For developers/contributors
├── FAQ.md                             # Frequently asked questions
├── TROUBLESHOOTING.md                 # Common issues and solutions
├── CHANGELOG.md                       # Version history
├── LICENSE.md                         # License information
├── planning/                          # EPIC and STORY files
│   ├── EPIC-001-*.md
│   └── STORY-*.md
├── architecture/                      # Architecture diagrams
│   ├── system_overview.png
│   ├── data_flow.png
│   └── database_schema.png
├── screenshots/                       # UI screenshots
│   ├── setup_wizard.png
│   ├── tag_review.png
│   └── results.png
└── examples/                          # Example configurations
    ├── config_minimal.yaml
    ├── config_full.yaml
    └── preferences_export.json
```

### README.md Template

```markdown
# Automated Image Tagging and File Sorting System

**Automated anime image tagging using booru databases + AI content analysis + preference learning**

![System Overview](docs/architecture/system_overview.png)

## ✨ Features

- 🔍 **Reverse Image Search** - Find tags from SauceNAO, IQDB, and Danbooru
- 🏷️ **XMP Sidecar Metadata** - Non-destructive tagging compatible with Immich
- 🤖 **AI Content Analysis** - CLIP and Faster R-CNN for intelligent categorization
- 🧠 **Preference Learning** - System learns from your corrections
- 📁 **Automatic Organization** - Sort images into category folders
- 🔄 **NAS Sync** - Robocopy-based sync to Synology NAS
- ⚡ **High Performance** - Process 1,000 images in ~45 minutes

## 🚀 Quick Start

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/ai-file-sorter.git
cd ai-file-sorter

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download ExifTool
# Download from https://exiftool.org/ and add to PATH

# 4. Run setup wizard
python -m src.utils.setup_wizard

# 5. Verify installation
python -m src.utils.verify_setup
```

### Basic Usage

```bash
# Process images in inbox
python -m src.main process --auto-approve

# With tag review
python -m src.main process --review

# Validate uma.json files
python -m src.utils.uma_validator_cli /path/to/json/files -o /path/to/validated
```

## 📋 Requirements

- **OS:** Windows 11 (primary target)
- **Python:** 3.9 or higher
- **RAM:** 8GB minimum (16GB recommended)
- **Disk:** 10GB free space (for models and cache)
- **Network:** For API calls to SauceNAO and Danbooru

## 📖 Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [User Guide](docs/USER_GUIDE.md) - How to use the system
- [Configuration Reference](docs/CONFIGURATION.md) - All config options
- [API Integration](docs/API_INTEGRATION.md) - Setting up API keys
- [Architecture](docs/ARCHITECTURE.md) - Technical details
- [FAQ](docs/FAQ.md) - Common questions

## 🎯 Workflow

```
Inbox → Reverse Search → Tag Review → XMP Write →
AI Analysis → Categorization → NAS Sync → Immich
```

1. Place images in inbox folder
2. System finds tags via reverse image search
3. Review and approve tags (optional)
4. Tags written to XMP sidecars
5. AI analyzes content and suggests categories
6. Files organized into category folders
7. Synced to NAS for Immich access

## 🔧 Configuration

Configuration is managed via `config/config.yaml`:

```yaml
directories:
  inbox: "C:\\ImageProcessing\\Inbox"
  sorted: "C:\\ImageProcessing\\Sorted"
  nas_path: "Z:\\photos"

api:
  saucenao:
    api_key: "${SAUCENAO_API_KEY}"
  danbooru:
    username: "${DANBOORU_USER}"
    api_key: "${DANBOORU_API_KEY}"

content_analysis:
  enabled: true
```

See [Configuration Reference](docs/CONFIGURATION.md) for all options.

## 📊 Performance

| Metric | Target | Typical |
|--------|--------|---------|
| Reverse search | 200/day (free) | Rate limited |
| XMP writing | <60s per 1000 | ~30s per 1000 |
| AI analysis | <5min per 1000 | ~4min per 1000 |
| Complete workflow | <60min per 1000 | ~45min per 1000 |

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.

## 🙏 Acknowledgments

- [SauceNAO](https://saucenao.com/) - Reverse image search API
- [Danbooru](https://danbooru.donmai.us/) - Tag database
- [OpenAI CLIP](https://github.com/openai/CLIP) - Image classification
- [ExifTool](https://exiftool.org/) - Metadata manipulation
- [Immich](https://immich.app/) - Photo management

## 📧 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/ai-file-sorter/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/ai-file-sorter/discussions)

---

**Status:** Active Development | **Version:** 1.0.0 | **Updated:** 2025-11-12
```

### User Guide Template (Excerpt)

```markdown
# User Guide

## Getting Started

### First Time Setup

1. **Run Setup Wizard**
   ```bash
   python -m src.utils.setup_wizard
   ```

   The wizard will guide you through:
   - Setting up directories
   - Configuring API keys
   - Enabling content analysis
   - Configuring NAS sync

2. **Verify Installation**
   ```bash
   python -m src.utils.verify_setup
   ```

   This checks that all dependencies are installed correctly.

### API Keys Setup

#### SauceNAO

1. Visit https://saucenao.com/
2. Create account or log in
3. Go to https://saucenao.com/user.php
4. Generate API key
5. Add to `.env` file:
   ```
   SAUCENAO_API_KEY=your_key_here
   ```

**Free Tier:** 200 searches/day
**Paid Tiers:** Starting at $5/month for 10,000 searches/month

#### Danbooru

1. Visit https://danbooru.donmai.us/
2. Create account
3. Go to https://danbooru.donmai.us/profile
4. Generate API key
5. Add to `.env` file:
   ```
   DANBOORU_USER=your_username
   DANBOORU_API_KEY=your_key_here
   ```

**Note:** Gold+ account ($20/year) recommended for unlimited access.

## Processing Images

### Basic Workflow

1. **Place images in inbox**
   ```
   C:\ImageProcessing\Inbox\
   ```

2. **Run processing**
   ```bash
   python -m src.main process
   ```

3. **Review progress**
   - Progress bars show status
   - Logs written to `logs/image_tagger.log`

4. **Check results**
   - Sorted images in `C:\ImageProcessing\Sorted\`
   - Organized by category
   - XMP sidecars alongside each image

### Auto-Approve Mode

Skip tag review for faster processing:

```bash
python -m src.main process --auto-approve
```

Recommended for:
- High-confidence matches (80%+ similarity)
- Large batches (1000+ images)
- Second pass after manual corrections

### Tag Review Mode

Review and edit tags before applying:

```bash
python -m src.main process --review
```

For each image, you can:
- **[a]** Approve all tags
- **[e]** Edit tags manually
- **[r]** Reject (skip tagging)
- **[q]** Quit workflow

## Training Preferences

The system learns from your corrections over time.

### How It Works

1. **Initial Suggestions** - Based on AI analysis only
2. **User Corrections** - You move files to preferred categories
3. **Pattern Learning** - System detects patterns in corrections
4. **Improved Suggestions** - Future suggestions match your preferences

### Viewing Statistics

```bash
python -m src.main stats
```

Shows:
- Total movements tracked
- Correction rate
- Learned patterns
- Confidence scores

### Exporting Preferences

```bash
python -m src.main export-preferences preferences.json
```

### Resetting Preferences

```bash
python -m src.main reset-preferences
```

⚠️ Warning: This deletes all learned patterns!

## NAS Sync

### Setup

1. Mount Synology NAS share:
   ```
   net use Z: \\192.168.1.100\photos /persistent:yes
   ```

2. Update `config/config.yaml`:
   ```yaml
   directories:
     nas_path: "Z:\\photos\\sorted"

   sync:
     enabled: true
   ```

### Manual Sync

```bash
python -m src.main sync
```

### Automatic Sync

Sync happens automatically after processing if enabled in config.

## Troubleshooting

### "No matches found" for anime images

- Check API key is valid
- Verify similarity threshold (default: 70%)
- Try IQDB backup search
- Image may not be in booru databases

### "ExifTool not found"

1. Download from https://exiftool.org/
2. Add to PATH or configure path in `config.yaml`:
   ```yaml
   xmp:
     exiftool_path: "C:\\Tools\\exiftool.exe"
   ```

### Slow processing

- Enable content analysis caching
- Increase batch size
- Disable GUI review (use auto-approve)
- Use GPU if available

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more issues.
```

## Testing Strategy

### Documentation Review Checklist
- [ ] All links work correctly
- [ ] Code examples run without errors
- [ ] Screenshots are up-to-date
- [ ] Installation steps verified on clean Windows 11
- [ ] API instructions tested with real accounts
- [ ] Configuration examples are valid YAML

### User Testing
- [ ] Non-technical user can follow installation guide
- [ ] Quick start completes in <15 minutes
- [ ] User guide covers all common tasks
- [ ] FAQ addresses most common questions
- [ ] Troubleshooting guide resolves typical issues

## Definition of Done

- [ ] All acceptance criteria met
- [ ] README.md complete with quick start
- [ ] Installation guide tested on clean system
- [ ] User guide covers all features
- [ ] API integration guide with step-by-step instructions
- [ ] Architecture documentation with diagrams
- [ ] Developer guide for contributors
- [ ] FAQ and troubleshooting guide
- [ ] All documentation reviewed and approved
- [ ] Screenshots and diagrams created

## Dependencies

**Depends On:**
- STORY-010 (Testing - needs working system)

**Blocks:**
- None (final story)

## Notes

- Use clear, simple language for non-technical users
- Include plenty of examples and screenshots
- Keep README.md concise, link to detailed docs
- Consider video tutorials for complex topics

## Risks

- **Low Risk:** Documentation becomes outdated
  - *Mitigation:* Review docs with each release

## Related Files

- `/README.md`
- `/docs/*.md`
- `/docs/screenshots/`
- `/docs/architecture/`
- `/docs/examples/`

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
