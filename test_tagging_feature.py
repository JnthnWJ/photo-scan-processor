#!/usr/bin/env python3
"""Tests for session tagging and bulk move operations."""

import os
import sys
import tempfile

from PIL import Image
from PySide6.QtWidgets import QApplication

# Add the current directory to the path so we can import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from photo_metadata_editor_qt import PhotoMetadataEditor


def _create_test_photos(folder: str, count: int = 3):
    """Create JPEG files large enough to pass lightweight validation."""
    for index in range(count):
        image = Image.new('RGB', (1200, 900), color=(80 + index * 40, 120, 160))
        photo_path = os.path.join(folder, f"photo_{index + 1}.jpg")
        image.save(photo_path, "JPEG", quality=95)


def test_tagging_and_bulk_move():
    """Tag photos in-session and move by tag in one operation."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as destination_dir:
        _create_test_photos(source_dir, count=3)

        editor = PhotoMetadataEditor()
        editor.load_folder(source_dir)

        assert len(editor.photo_files) == 3

        # Tag first photo as Keepers.
        editor.tag_entry.setText("Keepers")
        editor.add_tag_to_current_photo()

        # Tag second photo as Keepers.
        editor._navigate_next()
        editor.tag_entry.setText("keepers")  # Case-insensitive dedupe check.
        editor.add_tag_to_current_photo()

        # Tag third photo as Archive.
        editor._navigate_next()
        editor.tag_entry.setText("Archive")
        editor.add_tag_to_current_photo()

        counts_before = editor._tag_counts()
        assert counts_before.get("keepers") == 2
        assert counts_before.get("archive") == 1

        moved, failed = editor.move_photos_for_tag("Keepers", destination_dir)
        assert len(moved) == 2
        assert len(failed) == 0

        # Session list should now contain only one photo (Archive-tagged).
        assert len(editor.photo_files) == 1
        remaining_photo = editor.photo_files[0]
        assert "archive" in editor.photo_tags.get(remaining_photo, set())

        source_jpgs = [name for name in os.listdir(source_dir) if name.lower().endswith('.jpg')]
        destination_jpgs = [name for name in os.listdir(destination_dir) if name.lower().endswith('.jpg')]

        assert len(source_jpgs) == 1
        assert len(destination_jpgs) == 2


if __name__ == "__main__":
    test_tagging_and_bulk_move()
    print("✓ Tagging feature test passed")
