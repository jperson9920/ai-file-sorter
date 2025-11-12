# STORY-005: Preference Learning System with SQLite

**Epic:** EPIC-001
**Story Points:** 5
**Priority:** P1 - High
**Status:** Ready for Development
**Assignee:** TBD
**Estimated Time:** 3-4 days

## User Story

As a **user**, I want the **system to learn from my categorization corrections** so that **it becomes more accurate over time and automatically sorts images according to my preferences**.

## Acceptance Criteria

### AC1: Database Schema
- [ ] Create SQLite database for preference tracking
- [ ] Table: `file_movements` - track all categorization decisions
- [ ] Table: `user_preferences` - store learned patterns with confidence scores
- [ ] Table: `category_corrections` - count corrections per category
- [ ] Table: `file_history` - complete movement chain with hashing
- [ ] Indexes on frequently queried fields (file_hash, category)

### AC2: Movement Tracking
- [ ] Record suggested category vs actual category for each file
- [ ] Track image characteristics (style, content, tags)
- [ ] Store SHA256 hash to identify files across renames
- [ ] Record timestamp of each movement
- [ ] Support multiple movements of same file

### AC3: Pattern Learning
- [ ] Detect patterns in user corrections
- [ ] Build rules like "anime + persons → Anime/Characters"
- [ ] Calculate confidence scores based on correction frequency
- [ ] Require minimum 50 samples before high confidence (70%+)
- [ ] Update patterns incrementally as new corrections arrive

### AC4: Category Suggestion
- [ ] Query learned preferences for new images
- [ ] Apply pattern matching to image characteristics
- [ ] Return suggested category with confidence score
- [ ] Fall back to default categorization if no patterns match
- [ ] Log suggestion accuracy for monitoring

### AC5: Preference Management
- [ ] Export preferences to JSON for backup
- [ ] Import preferences from backup
- [ ] Reset preferences (clear learning)
- [ ] View preference statistics (accuracy, confidence, sample counts)
- [ ] Prune old/obsolete patterns

### AC6: Performance
- [ ] Insert operations complete in <10ms
- [ ] Query operations complete in <50ms
- [ ] Support 100,000+ file movements
- [ ] Database file size stays reasonable (<100MB for 100k records)

## Technical Implementation

### Database Schema

```sql
-- src/learning/schema.sql

-- Track every file movement decision
CREATE TABLE IF NOT EXISTS file_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    suggested_category TEXT NOT NULL,
    actual_category TEXT NOT NULL,
    image_style TEXT,
    style_confidence REAL,
    persons_detected INTEGER,
    has_booru_tags BOOLEAN,
    tags_json TEXT,  -- JSON array of tags
    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_correction BOOLEAN,  -- TRUE if user overrode suggestion
    CONSTRAINT idx_file_hash INDEX (file_hash),
    CONSTRAINT idx_moved_at INDEX (moved_at)
);

-- Learned preference patterns
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_key TEXT UNIQUE NOT NULL,  -- e.g., "anime+persons"
    preferred_category TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.0,
    sample_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT idx_pattern_key INDEX (pattern_key),
    CONSTRAINT idx_confidence INDEX (confidence_score)
);

-- Category correction statistics
CREATE TABLE IF NOT EXISTS category_corrections (
    suggested_category TEXT NOT NULL,
    actual_category TEXT NOT NULL,
    correction_count INTEGER DEFAULT 0,
    last_corrected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (suggested_category, actual_category),
    CONSTRAINT idx_correction_count INDEX (correction_count DESC)
);

-- Complete file history (supports multiple moves)
CREATE TABLE IF NOT EXISTS file_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL,
    current_location TEXT NOT NULL,
    category TEXT NOT NULL,
    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    move_reason TEXT,  -- 'initial', 'recategorize', 'user_override'
    CONSTRAINT idx_file_hash_history INDEX (file_hash),
    CONSTRAINT idx_current_location INDEX (current_location)
);
```

### PreferenceTracker Class

```python
# src/learning/preference_tracker.py
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PreferenceTracker:
    """Track and learn from user categorization preferences."""

    def __init__(self, db_path: str):
        """Initialize preference tracker.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Read and execute schema
            schema_path = Path(__file__).parent / 'schema.sql'
            if schema_path.exists():
                with open(schema_path) as f:
                    conn.executescript(f.read())
            else:
                # Inline schema if file not found
                self._create_schema(conn)

        logger.info(f"Preference database initialized: {self.db_path}")

    def record_movement(
        self,
        file_path: Path,
        suggested_category: str,
        actual_category: str,
        content_analysis: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ):
        """Record a file categorization decision.

        Args:
            file_path: Path to image file
            suggested_category: System's suggested category
            actual_category: User's chosen category (may be same)
            content_analysis: Optional dict from ContentAnalyzer
            tags: Optional list of booru tags
        """
        # Generate file hash
        file_hash = self._hash_file(file_path)

        # Extract content analysis features
        style = None
        style_confidence = None
        persons_detected = None

        if content_analysis:
            style = content_analysis.get('style')
            style_confidence = content_analysis.get('style_confidence')
            persons_detected = content_analysis.get('persons_detected')

        # Was this a correction?
        is_correction = (suggested_category != actual_category)

        # Insert movement record
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO file_movements (
                    file_hash, file_path, suggested_category, actual_category,
                    image_style, style_confidence, persons_detected,
                    has_booru_tags, tags_json, is_correction
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_hash,
                str(file_path),
                suggested_category,
                actual_category,
                style,
                style_confidence,
                persons_detected,
                bool(tags),
                json.dumps(tags) if tags else None,
                is_correction
            ))

            # Update correction statistics if needed
            if is_correction:
                conn.execute('''
                    INSERT INTO category_corrections (suggested_category, actual_category, correction_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(suggested_category, actual_category)
                    DO UPDATE SET
                        correction_count = correction_count + 1,
                        last_corrected = CURRENT_TIMESTAMP
                ''', (suggested_category, actual_category))

            # Update file history
            conn.execute('''
                INSERT INTO file_history (file_hash, current_location, category, move_reason)
                VALUES (?, ?, ?, ?)
            ''', (
                file_hash,
                str(file_path),
                actual_category,
                'user_override' if is_correction else 'initial'
            ))

        # Learn from this correction
        if is_correction:
            self._update_patterns(
                content_analysis=content_analysis,
                tags=tags,
                preferred_category=actual_category
            )

        logger.debug(
            f"Recorded movement: {file_path.name} → {actual_category} "
            f"(correction: {is_correction})"
        )

    def _update_patterns(
        self,
        content_analysis: Optional[Dict],
        tags: Optional[List[str]],
        preferred_category: str
    ):
        """Update learned patterns based on correction.

        Args:
            content_analysis: Content analysis result
            tags: List of tags
            preferred_category: User's preferred category
        """
        # Generate pattern keys based on image characteristics
        pattern_keys = self._generate_pattern_keys(content_analysis, tags)

        with sqlite3.connect(self.db_path) as conn:
            for pattern_key in pattern_keys:
                # Upsert preference pattern
                conn.execute('''
                    INSERT INTO user_preferences (pattern_key, preferred_category, sample_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(pattern_key) DO UPDATE SET
                        sample_count = sample_count + 1,
                        last_updated = CURRENT_TIMESTAMP
                ''', (pattern_key, preferred_category))

                # Recalculate confidence score
                self._recalculate_confidence(conn, pattern_key)

    def _generate_pattern_keys(
        self,
        content_analysis: Optional[Dict],
        tags: Optional[List[str]]
    ) -> List[str]:
        """Generate pattern keys from image characteristics.

        Args:
            content_analysis: Content analysis result
            tags: List of tags

        Returns:
            List of pattern key strings
        """
        keys = []

        if not content_analysis:
            return keys

        style = content_analysis.get('style', '')
        style_confidence = content_analysis.get('style_confidence', 0)
        persons = content_analysis.get('persons_detected', 0)

        # High-confidence style patterns
        if style_confidence > 0.7:
            # Style alone
            keys.append(f"style:{style}")

            # Style + persons
            if persons > 0:
                keys.append(f"style:{style}+persons:yes")
            else:
                keys.append(f"style:{style}+persons:no")

        # Tag-based patterns (if available)
        if tags:
            # General pattern: has_booru_tags
            keys.append("tags:present")

            # Specific high-value tags
            anime_indicators = ['anime', 'manga', '1girl', '1boy', 'character']
            if any(t.lower() in anime_indicators for t in tags):
                keys.append("tags:anime_character")

        return keys

    def _recalculate_confidence(self, conn: sqlite3.Connection, pattern_key: str):
        """Recalculate confidence score for a pattern.

        Confidence increases with sample count:
        - <10 samples: low confidence (0.3)
        - 10-50 samples: medium confidence (0.5)
        - 50-100 samples: high confidence (0.7)
        - 100+ samples: very high confidence (0.9)

        Args:
            conn: Database connection
            pattern_key: Pattern to update
        """
        cursor = conn.execute(
            'SELECT sample_count FROM user_preferences WHERE pattern_key = ?',
            (pattern_key,)
        )
        row = cursor.fetchone()

        if not row:
            return

        sample_count = row[0]

        # Calculate confidence based on sample count
        if sample_count < 10:
            confidence = 0.3
        elif sample_count < 50:
            confidence = 0.5
        elif sample_count < 100:
            confidence = 0.7
        else:
            confidence = min(0.9, 0.7 + (sample_count - 100) / 1000)

        # Update confidence
        conn.execute(
            'UPDATE user_preferences SET confidence_score = ? WHERE pattern_key = ?',
            (confidence, pattern_key)
        )

    def suggest_category(
        self,
        content_analysis: Optional[Dict],
        tags: Optional[List[str]],
        default_category: str = "Uncategorized"
    ) -> Tuple[str, float]:
        """Suggest category based on learned preferences.

        Args:
            content_analysis: Content analysis result
            tags: List of tags
            default_category: Default if no pattern matches

        Returns:
            Tuple of (suggested_category, confidence)
        """
        pattern_keys = self._generate_pattern_keys(content_analysis, tags)

        if not pattern_keys:
            return (default_category, 0.0)

        # Query preferences for matching patterns
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' * len(pattern_keys))
            cursor = conn.execute(f'''
                SELECT preferred_category, confidence_score, sample_count
                FROM user_preferences
                WHERE pattern_key IN ({placeholders})
                ORDER BY confidence_score DESC, sample_count DESC
                LIMIT 1
            ''', pattern_keys)

            row = cursor.fetchone()

            if row:
                category, confidence, sample_count = row
                logger.debug(
                    f"Pattern match: {category} "
                    f"(confidence: {confidence:.2f}, samples: {sample_count})"
                )
                return (category, confidence)

        return (default_category, 0.0)

    def get_statistics(self) -> Dict:
        """Get preference learning statistics.

        Returns:
            Dict with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Total movements
            total_movements = conn.execute(
                'SELECT COUNT(*) FROM file_movements'
            ).fetchone()[0]

            # Corrections count
            corrections = conn.execute(
                'SELECT COUNT(*) FROM file_movements WHERE is_correction = 1'
            ).fetchone()[0]

            # Learned patterns
            patterns = conn.execute(
                'SELECT COUNT(*) FROM user_preferences'
            ).fetchone()[0]

            # High-confidence patterns (70%+)
            high_confidence = conn.execute(
                'SELECT COUNT(*) FROM user_preferences WHERE confidence_score >= 0.7'
            ).fetchone()[0]

            # Top corrections
            top_corrections = conn.execute('''
                SELECT suggested_category, actual_category, correction_count
                FROM category_corrections
                ORDER BY correction_count DESC
                LIMIT 5
            ''').fetchall()

        return {
            'total_movements': total_movements,
            'corrections': corrections,
            'correction_rate': corrections / total_movements if total_movements > 0 else 0,
            'learned_patterns': patterns,
            'high_confidence_patterns': high_confidence,
            'top_corrections': [
                {
                    'from': row[0],
                    'to': row[1],
                    'count': row[2]
                }
                for row in top_corrections
            ]
        }

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        """Generate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest string
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
```

### Database Utility Functions

```python
# src/learning/database.py
import sqlite3
from pathlib import Path
import json
from typing import Dict
import logging

logger = logging.getLogger(__name__)

def export_preferences(db_path: Path, export_path: Path):
    """Export preferences to JSON file.

    Args:
        db_path: Path to database
        export_path: Path to export JSON
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute('SELECT * FROM user_preferences')
        preferences = [
            {
                'pattern_key': row[1],
                'preferred_category': row[2],
                'confidence_score': row[3],
                'sample_count': row[4],
                'last_updated': row[5]
            }
            for row in cursor.fetchall()
        ]

    with open(export_path, 'w') as f:
        json.dump(preferences, f, indent=2)

    logger.info(f"Exported {len(preferences)} preferences to {export_path}")

def import_preferences(db_path: Path, import_path: Path):
    """Import preferences from JSON file.

    Args:
        db_path: Path to database
        import_path: Path to import JSON
    """
    with open(import_path) as f:
        preferences = json.load(f)

    with sqlite3.connect(db_path) as conn:
        for pref in preferences:
            conn.execute('''
                INSERT OR REPLACE INTO user_preferences
                (pattern_key, preferred_category, confidence_score, sample_count)
                VALUES (?, ?, ?, ?)
            ''', (
                pref['pattern_key'],
                pref['preferred_category'],
                pref['confidence_score'],
                pref['sample_count']
            ))

    logger.info(f"Imported {len(preferences)} preferences from {import_path}")

def reset_preferences(db_path: Path):
    """Clear all learned preferences.

    Args:
        db_path: Path to database
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute('DELETE FROM user_preferences')
        conn.execute('DELETE FROM category_corrections')
        logger.warning("All learned preferences have been reset")
```

## Testing Strategy

### Unit Tests

```python
# tests/test_learning/test_preference_tracker.py
def test_record_movement(tmp_path):
    db_path = tmp_path / "test.db"
    tracker = PreferenceTracker(str(db_path))

    # Create test image
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(b"fake image data")

    # Record movement
    tracker.record_movement(
        file_path=image_path,
        suggested_category="Photos/Other",
        actual_category="Anime/Characters",
        content_analysis={
            'style': 'anime style illustration',
            'style_confidence': 0.85,
            'persons_detected': 1
        },
        tags=['naruto', 'hinata']
    )

    # Verify recorded
    stats = tracker.get_statistics()
    assert stats['total_movements'] == 1
    assert stats['corrections'] == 1

def test_pattern_learning(tmp_path):
    db_path = tmp_path / "test.db"
    tracker = PreferenceTracker(str(db_path))

    # Simulate 60 corrections: anime+persons → Anime/Characters
    for i in range(60):
        image_path = tmp_path / f"test_{i}.jpg"
        image_path.write_bytes(b"fake")

        tracker.record_movement(
            file_path=image_path,
            suggested_category="Uncategorized",
            actual_category="Anime/Characters",
            content_analysis={
                'style': 'anime style illustration',
                'style_confidence': 0.85,
                'persons_detected': 1
            }
        )

    # After 60 samples, should have high confidence
    category, confidence = tracker.suggest_category(
        content_analysis={
            'style': 'anime style illustration',
            'style_confidence': 0.85,
            'persons_detected': 1
        },
        tags=None
    )

    assert category == "Anime/Characters"
    assert confidence >= 0.7  # High confidence
```

### Integration Tests

```python
def test_full_learning_cycle():
    """Test complete learning cycle with real corrections."""
    tracker = PreferenceTracker('test.db')

    # 1. Initial suggestion (no learning yet)
    category, confidence = tracker.suggest_category(
        content_analysis={'style': 'anime style illustration', 'style_confidence': 0.9, 'persons_detected': 2},
        tags=None,
        default_category="Uncategorized"
    )
    assert confidence < 0.5  # Low confidence initially

    # 2. Record 100 corrections with same pattern
    for i in range(100):
        tracker.record_movement(
            file_path=Path(f'test_{i}.jpg'),
            suggested_category="Uncategorized",
            actual_category="Anime/Characters",
            content_analysis={'style': 'anime style illustration', 'style_confidence': 0.9, 'persons_detected': 2}
        )

    # 3. Now suggestion should have high confidence
    category, confidence = tracker.suggest_category(
        content_analysis={'style': 'anime style illustration', 'style_confidence': 0.9, 'persons_detected': 2},
        tags=None
    )
    assert category == "Anime/Characters"
    assert confidence >= 0.7  # High confidence after 100 samples
```

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests pass with 85%+ coverage
- [ ] Integration tests verify learning cycle
- [ ] Performance test: 100k movements in database
- [ ] Export/import preferences works correctly
- [ ] Statistics dashboard implemented
- [ ] Database schema documented
- [ ] Code reviewed and approved

## Dependencies

**Depends On:**
- STORY-001 (Project setup)
- STORY-004 (Content analysis provides input features)

**Blocks:**
- STORY-008 (Workflow uses preference suggestions)

## Notes

- SQLite is sufficient for local single-user application
- Consider periodic database VACUUM for optimization
- Pattern matching can be extended with more sophisticated rules
- Confidence calculation is simplistic but effective

## Risks

- **Low Risk:** Database corruption
  - *Mitigation:* Regular exports, backup before reset

## Related Files

- `/src/learning/preference_tracker.py`
- `/src/learning/database.py`
- `/src/learning/schema.sql`
- `/tests/test_learning/`
- `/data/preferences.db`

---

**Created:** 2025-11-12
**Last Updated:** 2025-11-12
