"""
Test suite for scanner backend functionality.

Tests code extraction, validation, and comment processing.
"""

import sys
from pathlib import Path

# Setup path to allow imports from parent directory
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import app as backend_app


class TestCodeExtraction:
    """Tests for code extraction functionality."""

    def test_filters_blacklisted_words(self):
        """Ensure blacklisted words are filtered from extracted codes."""
        text = "Thanks! Here is ABC123 and PLEASE, also ZZ99ZZ and NOBODY."
        matches = backend_app.extract_codes_from_body(text)

        assert "ABC123" in matches, "Valid code should be extracted"
        assert "PLEASE" not in matches, "Blacklisted word should be filtered"
        assert "NOBODY" not in matches, "Blacklisted word should be filtered"

    def test_parses_multiple_codes(self):
        """Verify multiple valid codes are extracted from text."""
        text = "New codes: QR12TY, ab12cd, and works? nope."
        matches = backend_app.extract_codes_from_body(text)

        assert {"QR12TY", "AB12CD"}.issubset(set(matches)), \
            "All valid codes should be extracted and normalized"


class TestCodeValidation:
    """Tests for code validation logic."""

    def test_valid_code_format(self):
        """Test that properly formatted codes pass validation."""
        assert backend_app.is_valid_candidate("AB12CD") is True, \
            "Code with letters and numbers should be valid"

    def test_invalid_code_formats(self):
        """Test that improperly formatted codes fail validation."""
        assert backend_app.is_valid_candidate("ABCDEF") is False, \
            "Code with only letters should be invalid"
        assert backend_app.is_valid_candidate("123456") is False, \
            "Code with only numbers should be invalid"
        assert backend_app.is_valid_candidate("AB1CDE") is False, \
            "Code with improper format should be invalid"


class TestCommentProcessing:
    """Tests for comment iteration and processing."""

    def test_flattens_nested_comment_tree(self):
        """Verify nested comment structures are flattened correctly."""
        listing = [
            {
                "data": {
                    "id": "1",
                    "body": "Root comment",
                    "replies": {
                        "data": {
                            "children": [
                                {
                                    "data": {
                                        "id": "1.1",
                                        "body": "Nested comment",
                                    }
                                }
                            ]
                        }
                    },
                }
            }
        ]

        flattened = list(backend_app.iter_comments(listing))
        comment_ids = {item.get("id") for item in flattened}

        assert comment_ids == {"1", "1.1"}, \
            "Both root and nested comments should be extracted"
