#!/usr/bin/env python3
"""
Test script for the PySide6 Photo Metadata Editor
"""

import sys
import os
from photo_metadata_editor_qt import PhotoMetadataEditor
from PySide6.QtWidgets import QApplication

def test_basic_functionality():
    """Test basic application functionality."""
    print("Testing PySide6 Photo Metadata Editor...")
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = PhotoMetadataEditor()
    
    # Test window creation
    assert window.windowTitle() == "Photo Metadata Editor"
    assert window.minimumSize().width() == 800
    assert window.minimumSize().height() == 600
    
    # Test UI components exist
    assert hasattr(window, 'photo_label')
    assert hasattr(window, 'metadata_scroll')
    assert hasattr(window, 'date_entry')
    assert hasattr(window, 'caption_text')
    assert hasattr(window, 'location_entry')
    assert hasattr(window, 'status_bar')
    
    # Test initial state
    assert window.current_folder is None
    assert len(window.photo_files) == 0
    assert window.current_photo_index == 0
    
    print("✓ Basic functionality tests passed")
    
    # Show window for manual testing
    window.show()
    
    print("Application window opened. Test the following:")
    print("1. Click 'Select Folder' and choose a folder with JPEG images")
    print("2. Use arrow keys to navigate between photos")
    print("3. Test trackpad scrolling in the metadata panel (right side)")
    print("4. Edit metadata fields and verify auto-save")
    print("5. Test location geocoding by typing a location name")
    print("6. Press Ctrl+O to open folder dialog")
    print("7. Press Esc to hide location suggestions")
    print("\nClose the window when done testing.")
    
    # Run the application
    return app.exec()

if __name__ == "__main__":
    exit_code = test_basic_functionality()
    print(f"Application exited with code: {exit_code}")
