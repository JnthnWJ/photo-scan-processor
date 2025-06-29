#!/usr/bin/env python3
"""
Test script for recent values functionality in the Photo Metadata Editor.
Tests storage, display, selection, and persistence of recent date and location values.
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime

# Add the current directory to the path so we can import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from photo_metadata_editor_qt import PhotoMetadataEditor


def create_test_photos(test_dir):
    """Create test photos with basic EXIF data."""
    import piexif
    from PIL import Image
    
    photo_paths = []
    
    for i in range(3):
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo_path = os.path.join(test_dir, f"test_photo_{i+1}.jpg")
        img.save(photo_path, "JPEG")
        photo_paths.append(photo_path)
    
    return photo_paths


def test_recent_values_storage():
    """Test the storage and retrieval of recent values."""
    print("Testing recent values storage...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create a temporary directory for test photos
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create test photos
        photo_paths = create_test_photos(test_dir)
        
        # Create editor instance with custom recent values file
        editor = PhotoMetadataEditor()
        editor.recent_values_file = os.path.join(test_dir, "test_recent_values.json")
        
        # Test adding date values
        test_dates = ["January 1, 2023", "February 15, 2023", "March 30, 2023", "April 10, 2023"]
        for date in test_dates:
            editor.add_recent_date_value(date)
        
        # Should only keep last 3
        assert len(editor.recent_date_values) == 3
        assert editor.recent_date_values == ["February 15, 2023", "March 30, 2023", "April 10, 2023"]
        
        # Test adding location values
        test_locations = ["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX"]
        for location in test_locations:
            editor.add_recent_location_value(location)
        
        # Should only keep last 3
        assert len(editor.recent_location_values) == 3
        assert editor.recent_location_values == ["Los Angeles, CA", "Chicago, IL", "Houston, TX"]
        
        # Test duplicate handling
        editor.add_recent_date_value("February 15, 2023")  # Already exists
        assert len(editor.recent_date_values) == 3
        assert editor.recent_date_values == ["March 30, 2023", "April 10, 2023", "February 15, 2023"]
        
        print("✓ Recent values storage tests passed")
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)


def test_recent_values_persistence():
    """Test that recent values persist across application sessions."""
    print("Testing recent values persistence...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create a temporary directory for test
    test_dir = tempfile.mkdtemp()
    recent_values_file = os.path.join(test_dir, "test_recent_values.json")
    
    try:
        # First session - add some values
        editor1 = PhotoMetadataEditor()
        editor1.recent_values_file = recent_values_file
        
        editor1.add_recent_date_value("January 1, 2023")
        editor1.add_recent_date_value("February 15, 2023")
        editor1.add_recent_location_value("New York, NY")
        editor1.add_recent_location_value("Los Angeles, CA")
        
        # Verify file was created
        assert os.path.exists(recent_values_file)
        
        # Second session - load values
        editor2 = PhotoMetadataEditor()
        editor2.recent_values_file = recent_values_file
        editor2.load_recent_values()
        
        # Verify values were loaded
        assert editor2.recent_date_values == ["January 1, 2023", "February 15, 2023"]
        assert editor2.recent_location_values == ["New York, NY", "Los Angeles, CA"]
        
        print("✓ Recent values persistence tests passed")
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)


def test_recent_values_ui_display():
    """Test the UI display of recent values."""
    print("Testing recent values UI display...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create a temporary directory for test photos
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create test photos
        photo_paths = create_test_photos(test_dir)
        
        # Create editor instance
        editor = PhotoMetadataEditor()
        editor.recent_values_file = os.path.join(test_dir, "test_recent_values.json")
        
        # Load test folder
        editor.load_folder(test_dir)
        
        # Add some recent values
        editor.add_recent_date_value("January 1, 2023")
        editor.add_recent_date_value("February 15, 2023")
        editor.add_recent_location_value("New York, NY")
        editor.add_recent_location_value("Los Angeles, CA")

        print(f"Recent date values: {editor.recent_date_values}")
        print(f"Recent location values: {editor.recent_location_values}")
        
        # Test showing recent date values
        editor.show_date_recent_values()
        print(f"Date recent frame visible: {editor.date_recent_frame.isVisible()}")
        print(f"Date recent layout count: {editor.date_recent_layout.count()}")
        assert editor.date_recent_frame.isVisible()
        assert editor.date_recent_layout.count() == 2  # 2 recent values

        # Test showing recent location values
        editor.show_location_recent_values()
        print(f"Location recent frame visible: {editor.location_recent_frame.isVisible()}")
        print(f"Location recent layout count: {editor.location_recent_layout.count()}")
        assert editor.location_recent_frame.isVisible()
        assert editor.location_recent_layout.count() == 2  # 2 recent values
        
        # Test hiding recent values
        editor.hide_date_recent_values()
        assert not editor.date_recent_frame.isVisible()
        
        editor.hide_location_recent_values()
        assert not editor.location_recent_frame.isVisible()
        
        print("✓ Recent values UI display tests passed")
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)


def test_recent_values_interaction():
    """Test interaction between recent values and field changes."""
    print("Testing recent values interaction...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create a temporary directory for test photos
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create test photos
        photo_paths = create_test_photos(test_dir)
        
        # Create editor instance
        editor = PhotoMetadataEditor()
        editor.recent_values_file = os.path.join(test_dir, "test_recent_values.json")
        
        # Load test folder
        editor.load_folder(test_dir)
        
        # Add some recent values
        editor.add_recent_date_value("January 1, 2023")
        editor.add_recent_location_value("New York, NY")
        
        # Test that recent values show when fields are empty
        editor.date_entry.clear()
        editor.location_entry.clear()
        editor.on_date_change()
        editor.on_location_change()
        
        # Recent values should be visible for empty fields
        assert editor.date_recent_frame.isVisible()
        assert editor.location_recent_frame.isVisible()
        
        # Test that recent values hide when user types
        editor.date_entry.setText("test")
        editor.on_date_change()
        assert not editor.date_recent_frame.isVisible()
        
        editor.location_entry.setText("test")
        editor.on_location_change()
        assert not editor.location_recent_frame.isVisible()
        
        print("✓ Recent values interaction tests passed")
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)


def run_all_tests():
    """Run all recent values tests."""
    print("Running recent values functionality tests...\n")
    
    try:
        test_recent_values_storage()
        test_recent_values_persistence()
        test_recent_values_ui_display()
        test_recent_values_interaction()
        
        print("\n✅ All recent values tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
