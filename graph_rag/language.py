"""
Multi-Language Support

Language detection and multi-language query support for Graph RAG.

Supported languages:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Chinese (zh)

Target CC: ≤5 per method (Phase 1 standards)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Detect language of query text.

    Uses simple heuristics based on character patterns and common words.
    Falls back to English if detection is uncertain.

    Target CC: ≤3 per method
    """

    # Language detection patterns and common words
    LANGUAGE_PATTERNS = {
        "zh": {
            "chars": [
                # Common Chinese characters (CJK) - check first due to high specificity
                "\u4e00", "\u4e8c", "\u4e09", "\u4e94",  # numbers
                "\u6211", "\u4f60", "\u4ed6", "\u4e16", "\u754c",  # common chars
                "\u662f", "\u4ec0", "\u9ebc", "\u8b02", "\u7684", "\u4e86", "\u9ba4", "\u5143"  # more common
            ],
            "weight": 10  # High weight for special characters
        },
        "es": {
            "chars": ["ñ", "¿", "¡"],  # Most specific Spanish chars
            # Include common Spanish words that naturally appear in simple Spanish text
            "words": ["hola", "mundo", "qué", "está", "cómo", "dónde", "cuál", "para", "por", "gracias", "sí", "buenos"],
            "weight": 3
        },
        "fr": {
            "chars": ["«", "»", "ç"],  # Most specific French chars
            "words": ["qu'est", "pourquoi", "comment", "où", "quel", "être", "bonjour"],
            "weight": 3
        },
        "de": {
            "chars": ["ß"],  # Most specific German char
            # Note: "und" only counts if not part of larger word (handled by word boundary matching)
            "words": ["ist", "der", "die", "das", "wie", "machen", "hallo", "welt"],
            "weight": 3
        },
        "en": {
            "words": ["the", "is", "and", "to", "what", "how", "why", "where", "hello", "world"],
            "weight": 1  # Default/lowest weight
        }
    }

    def __init__(self):
        """Initialize language detector.

        CC: 1 (simple init)
        """
        pass

    def _score_chars(self, text: str, patterns: dict) -> int:
        """Score language by character pattern matches.

        Args:
            text: Original text (not lowered, for char matching)
            patterns: Language pattern dict with optional 'chars' and 'weight'

        Returns:
            Character-based score (0 if no char patterns defined)
        """
        if "chars" not in patterns:
            return 0
        weight = patterns.get("weight", 1)
        char_matches = sum(text.count(c) for c in patterns["chars"])
        return char_matches * weight * 10 if char_matches > 0 else 0

    def _score_words(self, text_lower: str, patterns: dict) -> int:
        """Score language by word pattern matches with word boundaries.

        Args:
            text_lower: Lowercased text for word matching
            patterns: Language pattern dict with optional 'words' and 'weight'

        Returns:
            Word-based score (0 if no word patterns defined)
        """
        if "words" not in patterns:
            return 0
        weight = patterns.get("weight", 1)
        word_matches = 0
        for word in patterns["words"]:
            if len(word) > 2:
                pat = r'\b' + re.escape(word) + r'\b'
                word_matches += len(re.findall(pat, text_lower))
        return word_matches * weight * 3 if word_matches > 0 else 0

    def _select_best_language(self, scores: dict) -> str:
        """Select language with highest score, default to English.

        Args:
            scores: Dict of lang_code → score

        Returns:
            Language code with highest score, or 'en' if all zero
        """
        if not scores or max(scores.values()) == 0:
            return "en"
        return max(scores, key=scores.get)

    def detect_language(self, text: str) -> str:
        """
        Detect language of given text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code (en, es, fr, de, zh)
        """
        if not text or not text.strip():
            return "en"

        text_lower = text.lower()
        scores = {}

        for lang in ["zh", "es", "fr", "de", "en"]:
            patterns = self.LANGUAGE_PATTERNS.get(lang, {})
            score = self._score_chars(text, patterns) + self._score_words(text_lower, patterns)
            scores[lang] = score
            if score > 50:
                return lang

        return self._select_best_language(scores)

    def get_language_name(self, lang_code: str) -> str:
        """
        Get human-readable language name.

        Args:
            lang_code: ISO 639-1 language code

        Returns:
            Language name in English

        CC: 2 (dict lookup)
        """
        names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "zh": "Chinese",
        }
        return names.get(lang_code, "Unknown")
