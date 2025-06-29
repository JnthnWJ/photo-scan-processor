#!/usr/bin/env python3
"""
Test script to verify the copy from previous photo functionality works correctly.
This test ensures that copied metadata is automatically saved without requiring manual interaction.
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Add the current directory to the path so we can import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from photo_metadata_editor_qt import PhotoMetadataEditor

def create_test_photos():
    """Create temporary test photos for testing."""
    test_dir = tempfile.mkdtemp()
    
    # Copy test photos to temp directory
    test_photos_dir = os.path.join(os.path.dirname(__file__), 'test_photos')
    if os.path.exists(test_photos_dir):
        for filename in os.listdir(test_photos_dir):
            if filename.endswith('.jpg'):
                src = os.path.join(test_photos_dir, filename)
                dst = os.path.join(test_dir, filename)
                shutil.copy2(src, dst)
    
    return test_dir

def test_copy_functionality():
    """Test that copy from previous photo functionality saves metadata automatically."""
    print("Testing copy from previous photo functionality...")
    
    # Create QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create test photos
    test_dir = create_test_photos()
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create the editor
        editor = PhotoMetadataEditor()
        
        # Load test photos
        editor.load_folder(test_dir)
        
        if not editor.photo_files:
            print("ERROR: No test photos found!")
            return False
        
        print(f"Loaded {len(editor.photo_files)} test photos")
        
        # Set up metadata for the first photo
        test_date = "January 15, 2023"
        test_caption = "Test caption for copy functionality"
        test_location_data = {
            'address': 'Test Location, Test City',
            'latitude': 37.7749,
            'longitude': -122.4194
        }
        
        # Set metadata on first photo
        editor.date_entry.setText(test_date)
        editor.caption_text.setPlainText(test_caption)
        editor.location_entry.setText(test_location_data['address'])
        editor._last_selected_location = test_location_data
        
        # Manually confirm the date to save it
        parsed_date = editor.parse_natural_date(test_date)
        if parsed_date:
            editor.apply_date_confirmation(parsed_date)
        
        # Save caption and location
        editor.schedule_metadata_save('caption', test_caption)
        editor.schedule_metadata_save('location', test_location_data)
        
        # Force save pending changes
        editor.save_pending_metadata()
        
        print("Set metadata on first photo:")
        print(f"  Date: {test_date}")
        print(f"  Caption: {test_caption}")
        print(f"  Location: {test_location_data['address']}")
        
        # Move to next photo
        if len(editor.photo_files) > 1:
            editor.next_photo()
            print("Moved to next photo")
            
            # Verify the copy button is enabled
            if not editor.copy_from_previous_btn.isEnabled():
                print("ERROR: Copy button should be enabled!")
                return False
            
            print("Copy button is enabled - good!")
            
            # Clear current fields to ensure copy actually sets them
            editor.date_entry.setText("")
            editor.caption_text.setPlainText("")
            editor.location_entry.setText("")
            editor._last_selected_location = None
            
            # Test the copy functionality
            print("Testing copy from previous photo...")
            editor.copy_from_previous_photo()
            
            # Check that fields were populated
            copied_date = editor.date_entry.text().strip()
            copied_caption = editor.caption_text.toPlainText().strip()
            copied_location = editor.location_entry.text().strip()
            
            print("After copying:")
            print(f"  Date field: '{copied_date}'")
            print(f"  Caption field: '{copied_caption}'")
            print(f"  Location field: '{copied_location}'")
            
            # Verify the fields were populated correctly
            success = True
            if not copied_date:
                print("ERROR: Date field was not populated!")
                success = False
            elif "January 15, 2023" not in copied_date:
                print(f"ERROR: Date field has unexpected value: '{copied_date}'")
                success = False
            
            if copied_caption != test_caption:
                print(f"ERROR: Caption field mismatch. Expected: '{test_caption}', Got: '{copied_caption}'")
                success = False
            
            if copied_location != test_location_data['address']:
                print(f"ERROR: Location field mismatch. Expected: '{test_location_data['address']}', Got: '{copied_location}'")
                success = False
            
            # Check that _last_selected_location was set (this indicates location was properly saved)
            if editor._last_selected_location != test_location_data:
                print("ERROR: _last_selected_location was not set correctly!")
                success = False
            
            # Check that pending changes were created (this indicates metadata will be saved)
            if 'date' not in editor.pending_changes:
                print("ERROR: Date was not scheduled for saving!")
                success = False
            
            if 'caption' not in editor.pending_changes:
                print("ERROR: Caption was not scheduled for saving!")
                success = False
            
            if 'location' not in editor.pending_changes:
                print("ERROR: Location was not scheduled for saving!")
                success = False
            
            if success:
                print("✓ SUCCESS: Copy functionality works correctly!")
                print("  - All fields were populated")
                print("  - Metadata was scheduled for automatic saving")
                print("  - No manual interaction with dropdowns required")
                return True
            else:
                print("✗ FAILURE: Copy functionality has issues")
                return False
        else:
            print("ERROR: Need at least 2 photos to test copy functionality")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            shutil.rmtree(test_dir)
            print(f"Cleaned up test directory: {test_dir}")
        except:
            pass

if __name__ == "__main__":
    success = test_copy_functionality()
    sys.exit(0 if success else 1)
