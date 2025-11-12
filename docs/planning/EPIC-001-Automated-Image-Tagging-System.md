# EPIC-001: Automated Image Tagging and File Sorting System for Windows 11

**Epic Owner:** Development Team
**Status:** In Planning
**Priority:** P0 - Critical
**Estimated Effort:** 7 weeks
**Target Platform:** Windows 11

## Executive Summary

Build a comprehensive automated image tagging and file sorting system that runs on Windows 11, leveraging booru reverse image search for human-curated tags, AI content analysis for intelligent categorization, and seamless integration with Synology NAS and Immich photo management.

## Business Value

- **Automation:** 90% automation of image tagging and organization workflow
- **Performance:** Process 1,000 images in ~45 minutes end-to-end
- **Quality:** 70-90% match rate for anime artwork with human-curated tags
- **Privacy:** Fully self-hosted solution with no cloud dependencies
- **Learning:** System improves accuracy over time through preference learning

## System Architecture

### Components

1. **Windows 11 Processing System** (Local)
   - Booru reverse image search (SauceNAO, IQDB, ASCII2D)
   - XMP sidecar metadata writer (ExifTool)
   - AI content analysis (CLIP + Faster R-CNN)
   - Preference learning (SQLite database)
   - File organization and categorization

2. **Synology NAS Integration** (Network)
   - Master photo library storage
   - Immich photo management (Docker)
   - SMB3 network shares
   - Automatic metadata sync

3. **Workflow Orchestration**
   - Automated batch processing
   - Robocopy sync to NAS
   - Scheduled task automation
   - Error handling and logging

### Data Flow

```
C:\ImageProcessing\Inbox\
    ↓
[1. Reverse Image Search] → SauceNAO/IQDB APIs
    ↓
[2. Tag Extraction] → Danbooru API
    ↓
[3. User Review & Approval] → Python GUI
    ↓
[4. XMP Sidecar Writing] → ExifTool
    ↓
[5. AI Content Analysis] → CLIP + Faster R-CNN
    ↓
[6. File Categorization] → Learned preferences
    ↓
[7. NAS Sync] → Robocopy to Synology
    ↓
[8. Immich Import] → External library scan
    ↓
Searchable in Immich Web UI
```

## Technical Specifications

### Windows 11 Requirements
- Python 3.9+
- ExifTool (Windows binary)
- PyTorch with CPU support
- 8GB RAM minimum
- 10GB disk space for models
- Gigabit ethernet for NAS connectivity

### Key Dependencies
- **saucenao-api:** Reverse image search
- **pybooru:** Danbooru tag scraping
- **PyExifTool:** XMP sidecar writing
- **transformers:** CLIP model (150MB)
- **torchvision:** Faster R-CNN (160MB)
- **Pillow:** Image processing
- **jsonschema:** JSON validation

### Performance Targets
- Reverse search: 200 images/day (free tier), 6 requests/30s
- XMP writing: 1,000 images in 30s (batch mode)
- AI analysis: 5 minutes per 1,000 images
- NAS sync: 100-300 MB/s over gigabit ethernet

## Stories Breakdown

### Phase 1: Foundation (Week 1-2)
- **STORY-001:** Project setup and environment configuration
- **STORY-002:** Booru reverse image search implementation
- **STORY-003:** XMP sidecar writer with ExifTool integration

### Phase 2: AI Enhancement (Week 3-4)
- **STORY-004:** Python content analysis module (CLIP + Faster R-CNN)
- **STORY-005:** Preference learning system with SQLite
- **STORY-006:** Database schema for file history tracking

### Phase 3: Integration (Week 5)
- **STORY-007:** Windows-to-NAS sync automation
- **STORY-008:** Workflow orchestration and batch processing
- **STORY-009:** JSON validation for uma.json files

### Phase 4: Polish (Week 6-7)
- **STORY-010:** Configuration management and setup scripts
- **STORY-011:** Error handling and logging infrastructure
- **STORY-012:** End-to-end testing and validation
- **STORY-013:** Documentation and user guide

## Success Criteria

### Functional Requirements
- ✅ Successfully tag 70%+ of anime images via reverse search
- ✅ Write XMP sidecars that Immich reads correctly
- ✅ Classify images by content (anime vs realistic, persons detected)
- ✅ Learn user preferences with 70%+ confidence after 100 corrections
- ✅ Sync to NAS with incremental updates
- ✅ Process 1,000 images in under 60 minutes

### Non-Functional Requirements
- ✅ Run entirely on Windows 11 without WSL
- ✅ No cloud dependencies (fully self-hosted)
- ✅ Non-destructive workflow (original images never modified)
- ✅ Handle network interruptions gracefully
- ✅ Comprehensive error logging
- ✅ Configuration via JSON/INI files

## Risk Assessment

### High Risk
- **API Rate Limits:** SauceNAO free tier limited to 200/day
  - *Mitigation:* Implement caching, use IQDB backup, consider paid tier

- **Model Performance:** CLIP/R-CNN may be slow on older CPUs
  - *Mitigation:* Batch processing, optional GPU support, smaller models

### Medium Risk
- **Network Reliability:** SMB connection to NAS may drop
  - *Mitigation:* Robocopy retry logic, resume support

- **Immich Compatibility:** XMP format may not parse correctly
  - *Mitigation:* Test multiple XMP formats, validate with sample library

### Low Risk
- **Disk Space:** Models and cache may consume significant space
  - *Mitigation:* Document requirements, implement cache cleanup

## Dependencies and Prerequisites

### External Systems
- Synology NAS with DSM 7.x (for full workflow)
- Immich deployed and accessible (for metadata search)
- SauceNAO API account (for reverse search)
- Danbooru account (for tag scraping)

### Development Environment
- Windows 11 PC with Python 3.9+
- Git for version control
- Visual Studio Code or similar IDE
- Network access to NAS (optional for testing)

## Timeline and Milestones

| Week | Milestone | Deliverables |
|------|-----------|--------------|
| 1 | Foundation Setup | Project structure, booru tagger, XMP writer |
| 2 | Core Workflow | Tag review UI, batch processing |
| 3 | AI Models | CLIP integration, Faster R-CNN detection |
| 4 | Learning System | SQLite schema, preference tracking |
| 5 | Integration | NAS sync, orchestration, uma.json validation |
| 6 | Testing | End-to-end tests, performance optimization |
| 7 | Documentation | User guide, setup scripts, README |

## Out of Scope

The following are explicitly **NOT** included in this epic:

- Immich deployment automation (assumes NAS already configured)
- Training custom ML models (using pre-trained only)
- Mobile app development
- Real-time file watching (scheduled batch processing only)
- Video file support (images only)
- Facial recognition (person detection only)

## Future Enhancements

Potential features for future iterations:

- GPU acceleration for faster inference
- Web UI for remote tag review
- Integration with additional booru sites (Gelbooru, etc.)
- Video thumbnail analysis
- Duplicate image detection
- Automatic album creation in Immich
- iCloud/Google Photos import automation

## Notes

- All file operations must be non-destructive (XMP sidecars only)
- System must work offline after initial setup (except reverse search)
- Windows native tools preferred over WSL/Linux dependencies
- Configuration should be user-editable (no hardcoded paths)
- Logging must be comprehensive for troubleshooting

## Related Documentation

- `/docs/compass_artifact_wf-c0099347-2c72-419d-b9f5-7570c07fef02_text_markdown.md` - Original requirements
- `/docs/planning/STORY-*.md` - Individual story specifications
- `/docs/architecture/` - Technical architecture diagrams (TBD)
- `/docs/api/` - API integration guides (TBD)

---

**Last Updated:** 2025-11-12
**Next Review:** Weekly during development
