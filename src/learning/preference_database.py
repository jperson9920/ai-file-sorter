"""SQLite database for tracking user preferences and learning patterns."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class PreferenceDatabase:
    """Database for tracking file movements and learning user preferences."""

    def __init__(self, db_path: str):
        """Initialize preference database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Preference database initialized: {self.db_path}")

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # File movements table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS file_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    suggested_category TEXT,
                    actual_category TEXT NOT NULL,
                    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    style TEXT,
                    persons_detected INTEGER,
                    booru_tags TEXT,
                    INDEX idx_file_hash ON file_movements(file_hash),
                    INDEX idx_actual_category ON file_movements(actual_category)
                )
            ''')

            # User preferences table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_key TEXT UNIQUE NOT NULL,
                    pattern_value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    sample_count INTEGER DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Category corrections table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS category_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_category TEXT NOT NULL,
                    to_category TEXT NOT NULL,
                    correction_count INTEGER DEFAULT 1,
                    PRIMARY KEY (from_category, to_category)
                ) WITHOUT ROWID
            ''')

            conn.commit()

    def record_movement(
        self,
        file_hash: str,
        file_name: str,
        actual_category: str,
        suggested_category: Optional[str] = None,
        style: Optional[str] = None,
        persons_detected: Optional[int] = None,
        booru_tags: Optional[List[str]] = None
    ):
        """Record a file movement to learn from.

        Args:
            file_hash: SHA256 hash of file
            file_name: Name of the file
            actual_category: Where user actually moved the file
            suggested_category: Where system suggested
            style: Detected style (from content analysis)
            persons_detected: Number of persons detected
            booru_tags: Tags from booru search
        """
        tags_json = json.dumps(booru_tags) if booru_tags else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO file_movements
                (file_hash, file_name, suggested_category, actual_category,
                 style, persons_detected, booru_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file_hash, file_name, suggested_category, actual_category,
                  style, persons_detected, tags_json))

            # Record correction if suggestion was wrong
            if suggested_category and suggested_category != actual_category:
                self._record_correction(conn, suggested_category, actual_category)

            conn.commit()

        logger.debug(f"Recorded movement: {file_name} -> {actual_category}")

    def _record_correction(self, conn, from_category: str, to_category: str):
        """Record a category correction."""
        conn.execute('''
            INSERT INTO category_corrections (from_category, to_category, correction_count)
            VALUES (?, ?, 1)
            ON CONFLICT(from_category, to_category)
            DO UPDATE SET correction_count = correction_count + 1
        ''', (from_category, to_category))

    def learn_preference(
        self,
        pattern_key: str,
        pattern_value: str,
        category: str,
        increment: bool = True
    ):
        """Learn or update a preference pattern.

        Args:
            pattern_key: Type of pattern (e.g., 'style', 'tag', 'persons')
            pattern_value: Pattern value (e.g., 'anime', 'naruto', '2')
            category: Target category
            increment: Whether to increment sample count
        """
        with sqlite3.connect(self.db_path) as conn:
            # Check if preference exists
            cursor = conn.execute('''
                SELECT sample_count, confidence
                FROM user_preferences
                WHERE pattern_key = ? AND pattern_value = ?
            ''', (pattern_key, pattern_value))

            row = cursor.fetchone()

            if row:
                sample_count, confidence = row
                new_count = sample_count + 1 if increment else sample_count
                # Increase confidence with more samples (asymptotic to 1.0)
                new_confidence = min(0.95, confidence + 0.05)

                conn.execute('''
                    UPDATE user_preferences
                    SET category = ?, confidence = ?, sample_count = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE pattern_key = ? AND pattern_value = ?
                ''', (category, new_confidence, new_count, pattern_key, pattern_value))
            else:
                conn.execute('''
                    INSERT INTO user_preferences
                    (pattern_key, pattern_value, category, confidence, sample_count)
                    VALUES (?, ?, ?, 0.5, 1)
                ''', (pattern_key, pattern_value, category))

            conn.commit()

    def get_preference(self, pattern_key: str, pattern_value: str) -> Optional[Dict]:
        """Get learned preference for a pattern.

        Args:
            pattern_key: Pattern type
            pattern_value: Pattern value

        Returns:
            Dict with 'category', 'confidence', 'sample_count' or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT category, confidence, sample_count
                FROM user_preferences
                WHERE pattern_key = ? AND pattern_value = ?
            ''', (pattern_key, pattern_value))

            row = cursor.fetchone()
            if row:
                return {
                    'category': row[0],
                    'confidence': row[1],
                    'sample_count': row[2]
                }

        return None

    def suggest_category(
        self,
        style: Optional[str] = None,
        persons_detected: Optional[int] = None,
        booru_tags: Optional[List[str]] = None,
        min_confidence: float = 0.7
    ) -> Optional[Dict]:
        """Suggest a category based on learned preferences.

        Args:
            style: Detected style
            persons_detected: Number of persons
            booru_tags: Tags from booru
            min_confidence: Minimum confidence threshold

        Returns:
            Dict with 'category', 'confidence', 'reason' or None
        """
        suggestions = []

        # Check style preference
        if style:
            pref = self.get_preference('style', style)
            if pref and pref['confidence'] >= min_confidence:
                suggestions.append({
                    'category': pref['category'],
                    'confidence': pref['confidence'],
                    'reason': f"style:{style}"
                })

        # Check persons preference
        if persons_detected is not None:
            pref = self.get_preference('persons', str(persons_detected))
            if pref and pref['confidence'] >= min_confidence:
                suggestions.append({
                    'category': pref['category'],
                    'confidence': pref['confidence'],
                    'reason': f"persons:{persons_detected}"
                })

        # Check tag preferences
        if booru_tags:
            for tag in booru_tags[:5]:  # Check top 5 tags
                pref = self.get_preference('tag', tag)
                if pref and pref['confidence'] >= min_confidence:
                    suggestions.append({
                        'category': pref['category'],
                        'confidence': pref['confidence'],
                        'reason': f"tag:{tag}"
                    })

        # Return highest confidence suggestion
        if suggestions:
            best = max(suggestions, key=lambda x: x['confidence'])
            return best

        return None

    def get_stats(self) -> Dict:
        """Get database statistics.

        Returns:
            Dict with counts and statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM file_movements')
            total_movements = cursor.fetchone()[0]

            cursor = conn.execute('SELECT COUNT(*) FROM user_preferences')
            total_preferences = cursor.fetchone()[0]

            cursor = conn.execute('''
                SELECT COUNT(*) FROM user_preferences WHERE confidence >= 0.7
            ''')
            high_confidence = cursor.fetchone()[0]

            return {
                'total_movements': total_movements,
                'total_preferences': total_preferences,
                'high_confidence_preferences': high_confidence
            }

    def export_preferences(self) -> Dict:
        """Export all preferences to JSON-serializable dict.

        Returns:
            Dict of all preferences
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT pattern_key, pattern_value, category, confidence, sample_count
                FROM user_preferences
                ORDER BY confidence DESC
            ''')

            preferences = []
            for row in cursor.fetchall():
                preferences.append({
                    'pattern_key': row[0],
                    'pattern_value': row[1],
                    'category': row[2],
                    'confidence': row[3],
                    'sample_count': row[4]
                })

            return {'preferences': preferences}

    def clear_all(self):
        """Clear all data from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM file_movements')
            conn.execute('DELETE FROM user_preferences')
            conn.execute('DELETE FROM category_corrections')
            conn.commit()

        logger.info("Cleared all preference data")
