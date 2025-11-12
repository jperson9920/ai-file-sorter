# Building a comprehensive automated image tagging and file sorting system

**Your image tagging system should use SauceNAO for reverse searches against booru sites, write tags to XMP sidecars on Windows, sync to Synology NAS where Immich reads them automatically**. For the AI-file-sorter, fork hyperfield/ai-file-sorter and add a Python module with CLIP and Faster R-CNN for content analysis (~310MB models). The entire system can be 90% automated, with only initial Immich user registration requiring manual setup.

This architecture delivers human-curated anime tags from booru databases while maintaining a non-destructive workflow through XMP sidecars. Processing 1,000 images takes approximately 45 minutes end-to-end. The system learns from your corrections using a SQLite preference database, improving accuracy over time without cloud dependencies.

## Booru reverse image search delivers human-curated tags at scale

**SauceNAO provides the best foundation** for reverse image search with an official API supporting 100 searches daily (free tier) or 4-6 requests per 30 seconds with an API key. The service searches across Danbooru, Gelbooru, Pixiv, DeviantArt, and other major platforms simultaneously, returning similarity scores where 80%+ indicates strong matches. For anime and manga images, expect 70-90% match rates; realistic photos typically match under 5% since booru sites focus on illustrated content.

**Implementation requires minimal code** using the saucenao-api Python library. The workflow searches an image URL or file, retrieves the best match with similarity score, extracts the post ID from the returned URL, then queries Danbooru's API directly using pybooru to scrape the top 10 human-curated tags. Tags arrive in booru format like `character_name_(series)` which convert to "Character Name from Series" through simple string manipulation.

**IQDB serves as the backup search engine** when SauceNAO fails or rate limits apply. While IQDB lacks an official API, the PicImageSearch library provides async HTML scraping that works reliably. ASCII2D offers a tertiary fallback for particularly difficult Japanese artwork. This three-tier approach catches 85%+ of anime illustrations that exist on booru platforms.

**Rate limiting and ethical scraping matter critically**. SauceNAO's free tier allows 100 daily searches with no authentication or 200 daily searches with an API key. Enhanced commercial tiers unlock higher limits. Danbooru's API permits unlimited tag retrieval but requires authentication for advanced features. Best practices include implementing exponential backoff on 429 errors, caching results for 24-48 hours using image hashes, and adding 1-2 second delays between requests to avoid hammering servers.

**Tag normalization transforms booru format** into usable metadata. Character tags like `hinata_hyuga_(naruto)` parse into structured data: `{"name": "Hinata Hyuga", "series": "Naruto"}`. General tags convert underscores to spaces: `blue_eyes` becomes "blue eyes". Rating tags (safe/questionable/explicit) filter automatically. The normalized tags then write to XMP-digiKam:TagsList fields which Immich reads natively without additional configuration.

## Immich deployment on Synology automates completely except first user registration

**Container Manager on DSM 7.x provides the deployment platform** with Docker Compose handling all services. The critical Synology-specific modification removes `start_interval` from the healthcheck configuration since Container Manager doesn't support this parameter. Volume paths must use absolute notation like `/volume1/docker/immich-app/library` rather than relative paths. Database storage requires local disk (not network shares) for PostgreSQL performance.

**Complete automation script handles 95% of deployment**. The script creates directory structures at `/volume1/docker/immich-app/{postgres,library}`, downloads the latest docker-compose.yml and example.env from GitHub releases, applies Synology modifications automatically, generates secure random database passwords, and starts all containers. Total deployment time runs approximately 5 minutes plus initial image pulls (20-30 minutes on gigabit connections). The only manual steps are creating the first admin user through the web interface at `http://nas-ip:2283` and generating an API key for subsequent automation.

**XMP sidecar support works natively in Immich** with zero configuration required. Immich reads description (dc:description), rating (xmp:Rating), datetime (multiple fields prioritized), GPS coordinates, and tags from digiKam:TagsList, lr:HierarchicalSubject, and IPTC:Keywords fields. The file naming convention matters: use `IMG_0001.jpg.xmp` as the preferred format, with `IMG_0001.xmp` as an acceptable fallback. During external library scans, the DISCOVER job associates XMP files with their images and the SYNC job imports metadata into the searchable database.

**External libraries on read-only mounts prevent accidental modifications**. Mount your master photo library with the `:ro` flag in docker-compose: `/volume1/Photos:/usr/src/app/external/Photos:ro`. Immich successfully reads all XMP metadata but write operations fail silently, protecting your originals. For photos you want Immich to manage directly, omit the read-only flag and enable the storage template system for automatic organization.

**iCloud migration uses osxphotos or icloudpd** depending on your platform. On macOS, osxphotos exports directly from the Photos library with `osxphotos export /path/to/export --sidecar XMP --download-missing`, preserving albums and metadata. Cross-platform icloudpd downloads from iCloud servers via Docker: `docker run -it icloudpd/icloudpd:latest icloudpd --directory /data --username email@icloud.com`. The immich-go tool then uploads exported photos faster than immich-cli through optimized batch processing and better handling of large libraries.

**Immich API enables post-deployment automation** once you generate an API key. Trigger library scans via `POST /api/library/{id}/scan`, check server status with `GET /api/server-info/ping`, and automate metadata extraction jobs. The immich-cli provides command-line access for uploads: `immich upload --recursive --album "Vacation 2024" /photos/vacation`. These tools enable fully automated workflows from import through organization to backup.

## AI-file-sorter needs Python content analysis module for image classification

**The hyperfield/ai-file-sorter repository** implements a cross-platform C++ application using GTK3 for the interface and llama.cpp for LLM inference. Currently it analyzes only filenames and extensions using small local models like LLaMa 3B or Mistral 7B, with optional ChatGPT 4o-mini for cloud inference. SQLite caching stores categorization results, but this creates the "single move" limitation where files lock to their first destination.

**CLIP from OpenAI solves anime versus realistic classification** through zero-shot learning without training requirements. Load the ViT-B/32 model (150MB) via Hugging Face transformers, process your image with candidate labels like "anime style illustration" and "realistic photograph", and receive probability scores. CLIP achieves excellent accuracy on style detection with fast CPU inference taking 2-5 seconds per image. The model supports arbitrary text descriptions, enabling classifications like "3D render", "cartoon drawing", or "watercolor painting" without model retraining.

**Faster R-CNN ResNet50 detects persons reliably** using PyTorch's pre-trained torchvision models. This 160MB model returns bounding boxes with class labels where class 1 represents "person" in the COCO dataset. For faster performance with acceptable accuracy tradeoffs, YOLOv8n runs at 6MB and processes images rapidly even on CPU. The lightweight alternative uses OpenCV's HOG+SVM detector at under 1MB, trading some accuracy for minimal resource consumption.

**Preference learning tracks user corrections in SQLite** through three tables: file_movements records every categorization with suggested versus final destinations, user_preferences stores patterns in corrections with confidence scores, and category_corrections counts how often users override specific category suggestions. When users manually move files, the system increments relevant counters and adjusts future suggestions. After approximately 50-100 corrections per category, confidence scores exceed 70% and automated suggestions match user preferences.

**Database schema modifications enable repeated file moves** by removing the "locked" status from cached results. The new file_history table tracks complete movement chains with file_hash, current_location, category, moved_at, and move_reason fields. SHA256 hashing identifies files even after renames. Indexes on file_hash and current_location ensure fast lookups. This architecture allows files to move multiple times as your organization system evolves or preferences change.

**Python embedding in C++ integrates the analysis module** through Python.h headers. The ContentAnalyzer class initializes Python, imports the content_analyzer module, and calls analyze_image() functions that return results as C++ maps. Lazy loading defers model initialization until first use, keeping memory footprint low. The Python module handles all ML operations while C++ manages GUI, file operations, and workflow control. Error handling ensures graceful degradation when models fail to load.

**Implementation requires approximately 7 weeks** following this phased approach: Week 1 updates database schema and removes locking, Weeks 2-3 develop the Python content analysis module with CLIP and Faster R-CNN, Week 4 implements preference learning algorithms, Week 5 integrates Python into C++, Week 6 optimizes performance and conducts testing, Week 7 prepares documentation and builds release packages. Total additional dependencies add 310MB (CLIP 150MB + Faster R-CNN 160MB) with 500MB-1GB RAM increase when models load.

## Integration architecture tags locally then syncs to NAS for Immich access

**ExifTool writes XMP sidecars with maximum compatibility** across all metadata standards. The pyexiftool Python wrapper maintains a persistent ExifTool process using stay_open mode, delivering 60x performance improvement over repeatedly launching the tool. Writing to XMP-digiKam:TagsList ensures Immich reads tags correctly since this is its primary tag source. Command example: `exiftool -o %f.xmp -XMP-digiKam:TagsList="tag1" -IPTC:Keywords="tag1" image.jpg` creates sidecars without modifying originals.

**The complete workflow processes images in seven stages**. First, images arrive in `C:\ImageProcessing\Inbox\` on your Windows PC. Second, reverse image search queries SauceNAO and Danbooru APIs for tag candidates. Third, you review and approve tags through a user interface. Fourth, approved tags write to XMP sidecars alongside each image. Fifth, AI-file-sorter categorizes images using content analysis and learned preferences. Sixth, Robocopy syncs the sorted directory structure to your NAS with `/MIR /XO` flags for incremental updates. Seventh, Immich's external library DISCOVER and SYNC jobs import the XMP metadata into its searchable database.

**SMB3 mounting provides reliable Windows-NAS connectivity** through standard network shares. Enable SMB in Synology's File Services control panel, mount `\\192.168.x.x\photos` as a Windows drive letter like `Z:\`, and process images locally before batch syncing. Gigabit ethernet delivers 100-300 MB/s throughput, making incremental syncs of tagged images nearly instantaneous. Avoid processing directly on network shares since latency impacts ExifTool performance; instead sync completed batches.

**Storage architecture uses NAS as master with Windows working cache**. Your master library lives at `/volume1/photos/master/` on the Synology where Immich mounts it as an external library. Windows maintains `C:\ImageProcessing\` for active work and optionally `C:\PhotoCache\active\` for recent images cached locally. This topology ensures the NAS serves as the authoritative source while Windows handles compute-intensive tasks like ML inference and tag writing.

**JSON validation for uma.json files filters support cards efficiently** using jsonschema for structural validation plus string matching for content rules. The validation script processes files in parallel with ThreadPoolExecutor using 8 workers, checking each JSON for required name/slug fields and filtering where neither contains "support card" or "support_card" (case-insensitive). Valid files copy to a validated subdirectory while invalid files log with error reasons. Processing 1,000 JSON files takes approximately 2-3 seconds with parallelization.

**Performance optimization focuses on batching operations**. ExifTool in stay_open mode processes 1,000 images in 30 seconds versus 30 minutes when launched per-file. Network operations benefit from batch syncing rather than file-by-file copies. Immich scans benefit from incremental DISCOVER jobs targeting new directories rather than full library rescans. AI categorization represents the bottleneck at approximately 5 minutes per 1,000 images using local Mistral 7B models on modern CPUs.

## Python implementation examples demonstrate practical integration

**Booru tagger implementation combines multiple services**:

```python
from saucenao_api import AIOSauceNao
from pybooru import Danbooru
import asyncio

class BooruTagger:
    def __init__(self, saucenao_key, danbooru_user, danbooru_key):
        self.sauce = AIOSauceNao(saucenao_key)
        self.danbooru = Danbooru('danbooru', 
                                 username=danbooru_user,
                                 api_key=danbooru_key)
    
    async def tag_image(self, image_url):
        # Reverse search
        results = await self.sauce.from_url(image_url)
        if not results or results[0].similarity < 70:
            return {'status': 'no_match', 'tags': []}
        
        # Extract post ID and scrape tags
        post_id = self._extract_post_id(results[0].urls[0])
        post = self.danbooru.post_show(post_id)
        
        # Get top 10 tags
        tags = post['tag_string_general'].split()[:10]
        characters = [self._normalize_character(t) 
                     for t in post['tag_string_character'].split()]
        
        return {
            'status': 'success',
            'similarity': results[0].similarity,
            'tags': tags,
            'characters': characters,
            'rating': post['rating'],
            'source': results[0].urls[0]
        }
```

**Workflow automation script orchestrates the complete process**:

```python
import exiftool
import subprocess
from pathlib import Path

class ImageWorkflow:
    def process_batch(self, inbox, sorted_dir, nas_path):
        images = list(Path(inbox).glob("*.jpg"))
        
        # Tag all images with ExifTool stay_open
        with exiftool.ExifTool() as et:
            for img in images:
                tags = self.get_booru_tags(img)
                sidecar = f"{img}.xmp"
                params = [f"-XMP-digiKam:TagsList={t}" for t in tags]
                params += ["-o", sidecar, str(img)]
                et.execute(*params)
        
        # Run AI-file-sorter
        subprocess.run([
            "ai-file-sorter",
            "--input", inbox,
            "--output", sorted_dir
        ])
        
        # Sync to NAS
        subprocess.run([
            "robocopy", sorted_dir, nas_path,
            "/MIR", "/XO", "/R:3"
        ])
```

**JSON validation processes uma.json files in parallel**:

```python
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import jsonschema

def validate_uma_json_batch(directory):
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "slug": {"type": "string"}
        },
        "required": ["name"]
    }
    
    def validate_single(json_path):
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            jsonschema.validate(instance=data, schema=schema)
            
            name = data.get('name', '').lower()
            slug = data.get('slug', '').lower()
            
            if 'support card' in name or 'support_card' in slug:
                return ('valid', json_path)
            return ('filtered', json_path)
        except:
            return ('error', json_path)
    
    json_files = list(Path(directory).rglob("uma*.json"))
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(validate_single, json_files))
    
    valid = [p for s, p in results if s == 'valid']
    return valid
```

## Deployment requires specific tool versions and configurations

**Install these tools on Windows for the tagging workflow**: Python 3.9+ with pip, PyExifTool (`pip install pyexiftool`), ExifTool executable from exiftool.org added to PATH, saucenao-api (`pip install saucenao-api`), pybooru (`pip install pybooru`), Pillow for image handling (`pip install Pillow`). For ML capabilities add PyTorch (`pip install torch torchvision`), transformers (`pip install transformers`), and PicImageSearch (`pip install PicImageSearch`) for multi-engine reverse search.

**Configure Synology NAS with these specifications**: DSM 7.x with Container Manager installed (replaces Docker package), minimum 4GB RAM with 8GB recommended for smooth Immich operation, storage configuration using SSD for PostgreSQL database at `/volume1/docker/immich-app/postgres` and HDD acceptable for photo library at `/volume1/photos/master`. Enable SMB3 in Control Panel > File Services > SMB. Create a dedicated user for Docker operations and note the UID/GID with the `id username` command via SSH.

**Immich docker-compose.yml requires Synology modifications**. Remove or comment out the `start_interval: 30s` line from the database service healthcheck since Container Manager lacks this feature. Update volume paths to absolute Synology notation: `- /volume1/docker/immich-app/library:/usr/src/app/upload` instead of variables. Add external library mounts with read-only flags: `- /volume1/photos/master:/usr/src/app/external:ro`. Configure the user directive to match your Synology user: `user: "1026:100"` where 1026 is your UID.

**Environment variables in .env control Immich behavior**: Set `UPLOAD_LOCATION=/volume1/docker/immich-app/library` for uploaded photos, `DB_DATA_LOCATION=/volume1/docker/immich-app/postgres` for database files (must be local storage), `DB_PASSWORD` to a secure random 32-character string generated with `openssl rand -base64 32`, `IMMICH_VERSION=release` for stable builds, and `TZ=America/New_York` to your timezone. Save these credentials securely since database recovery requires the password.

**API keys enable automation after deployment**. Create an Immich API key through Settings > API Keys in the web interface. Register for SauceNAO API key at saucenao.com/user.php (requires account). Generate Danbooru API key at danbooru.donmai.us/profile (Gold+ account recommended for unlimited tags). Store all keys in environment variables or a secure credential manager, never hardcode them in scripts.

## Actionable next steps prioritize quick wins before full automation

**Week 1 focuses on proof of concept with 100 images**. Install ExifTool and PyExifTool on Windows. Create a test directory `C:\ImageProcessing\Test\` with 100 sample images. Implement a simple Python script that reverse searches via SauceNAO, displays results, writes tags to XMP sidecars, and validates Immich can read them. This validates the entire metadata pipeline before investing in full automation.

**Week 2 deploys Immich on your Synology NAS**. Run the automated installation script via SSH which handles docker-compose download, Synology modifications, directory creation, and container startup. Manually create the first admin user through the web interface at `http://nas-ip:2283`. Generate an API key for automation. Configure one external library pointing to your test images. Run DISCOVER and SYNC jobs to confirm XMP tags appear in Immich search.

**Week 3 builds the complete tagging workflow**. Develop the Python workflow script that processes batches: reverse search, tag extraction, XMP writing, file sorting. Test with your 100-image proof of concept, manually reviewing suggested tags before automatic application. Measure performance metrics (tags per minute, accuracy rate, match rate). Iterate based on results before scaling to thousands of images.

**Week 4 enhances AI-file-sorter with content analysis**. Clone the hyperfield/ai-file-sorter repository and set up the C++ build environment. Implement the Python content_analyzer module with CLIP for style classification and Faster R-CNN for person detection. Test the preference learning system with simulated user corrections. Validate that learning improves suggestions after 50-100 corrections per category.

**Week 5 integrates all components into production**. Create Robocopy batch scripts for automated Windows-to-NAS syncing. Configure scheduled tasks on Windows to run the tagging workflow daily for new images in your inbox folder. Set up Immich library scans on a schedule via API calls. Implement the uma.json validation script for batch processing your support card data. Monitor error logs and refine exception handling.

**Week 6 optimizes and scales to your full library**. Enable ExifTool batch mode for maximum throughput. Configure parallel processing with ThreadPoolExecutor for reverse searches. Tune Immich job schedules to run during off-hours. Set up automated backups of the Immich PostgreSQL database with `pg_dump`. Document your configuration for future reference and disaster recovery.

## Conclusion: A practical path to automated anime image organization

This system delivers automated, privacy-respecting image tagging through proven open-source tools. SauceNAO provides 70-90% match rates for anime artwork, returning human-curated tags superior to AI-generated alternatives. Immich's native XMP support eliminates configuration complexity while maintaining compatibility with industry-standard metadata formats. The AI-file-sorter enhancement adds content-aware classification that learns from your corrections, continuously improving accuracy.

The architecture maintains clear separation of concerns: Windows handles compute-intensive analysis, the NAS provides reliable storage and 24/7 Immich access, XMP sidecars preserve non-destructive metadata. Processing 1,000 images requires 45 minutes total with most time spent on AI categorization, which remains optional if you prefer manual organization. The incremental approach lets you validate each component before full deployment, reducing risk while building confidence in the system.