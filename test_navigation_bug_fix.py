#!/usr/bin/env python3
"""
Test script to verify the navigation bug fix.
This script tests that rapid arrow key navigation doesn't delete existing metadata.
"""

import os
import sys
import tempfile
import shutil
import piexif
from datetime import datetime
from PIL import Image
import time

def create_test_photo_with_metadata(path, date_str, caption, location_data=None):
    """Create a test photo with EXIF metadata."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Create EXIF data
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # Add date
    if date_str:
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str.encode('utf-8')
    
    # Add caption
    if caption:
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = caption.encode('utf-8')
    
    # Add GPS data if provided
    if location_data:
        lat = location_data['latitude']
        lon = location_data['longitude']
        
        # Convert decimal degrees to GPS format
        lat_deg = int(abs(lat))
        lat_min = int((abs(lat) - lat_deg) * 60)
        lat_sec = int(((abs(lat) - lat_deg) * 60 - lat_min) * 60 * 100)
        
        lon_deg = int(abs(lon))
        lon_min = int((abs(lon) - lon_deg) * 60)
        lon_sec = int(((abs(lon) - lon_deg) * 60 - lon_min) * 60 * 100)
        
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [(lat_deg, 1), (lat_min, 1), (lat_sec, 100)]
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [(lon_deg, 1), (lon_min, 1), (lon_sec, 100)]
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
    
    # Save image with EXIF
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, "JPEG", exif=exif_bytes)

def read_metadata_from_photo(path):
    """Read metadata from a photo file."""
    try:
        exif_dict = piexif.load(path)
        metadata = {}
        
        # Read date
        if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            metadata['date'] = date_str
        
        # Read caption
        if "0th" in exif_dict and piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
            caption = exif_dict["0th"][piexif.ImageIFD.ImageDescription].decode('utf-8')
            metadata['caption'] = caption
        
        # Read GPS
        if "GPS" in exif_dict and piexif.GPSIFD.GPSLatitude in exif_dict["GPS"]:
            metadata['has_gps'] = True
        
        return metadata
    except Exception as e:
        print(f"Error reading metadata from {path}: {e}")
        return {}

def test_rapid_navigation_preserves_metadata():
    """Test that rapid navigation doesn't delete existing metadata."""
    print("Testing rapid navigation metadata preservation...")
    
    # Create temporary directory with test photos
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test photos with metadata
        test_photos = []
        for i in range(5):
            photo_path = os.path.join(temp_dir, f"test_photo_{i+1}.jpg")
            create_test_photo_with_metadata(
                photo_path,
                f"2023:01:{i+1:02d} 12:00:00",
                f"Test caption {i+1}",
                {'latitude': 37.7749 + i*0.01, 'longitude': -122.4194 + i*0.01}
            )
            test_photos.append(photo_path)
        
        # Read initial metadata
        initial_metadata = {}
        for photo in test_photos:
            initial_metadata[photo] = read_metadata_from_photo(photo)
            print(f"Initial metadata for {os.path.basename(photo)}: {initial_metadata[photo]}")
        
        print(f"\nCreated {len(test_photos)} test photos with metadata in {temp_dir}")
        print("To test the fix:")
        print("1. Run: python photo_metadata_editor_qt.py")
        print(f"2. Select folder: {temp_dir}")
        print("3. Rapidly press left/right arrow keys to navigate between photos")
        print("4. Don't make any metadata changes - just navigate quickly")
        print("5. After navigation, run this script again to verify metadata is preserved")
        
        # Wait for user to test
        input("\nPress Enter after testing navigation to verify metadata preservation...")
        
        # Check if metadata was preserved
        print("\nChecking metadata after navigation test...")
        all_preserved = True
        
        for photo in test_photos:
            current_metadata = read_metadata_from_photo(photo)
            initial = initial_metadata[photo]
            
            print(f"\n{os.path.basename(photo)}:")
            print(f"  Initial: {initial}")
            print(f"  Current: {current_metadata}")
            
            # Check if metadata was preserved
            if initial != current_metadata:
                print(f"  ❌ METADATA LOST!")
                all_preserved = False
            else:
                print(f"  ✅ Metadata preserved")
        
        if all_preserved:
            print("\n🎉 SUCCESS: All metadata was preserved during rapid navigation!")
        else:
            print("\n❌ FAILURE: Some metadata was lost during navigation!")
        
        return all_preserved

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-only":
        # Just verify existing photos in current directory
        photos = [f for f in os.listdir('.') if f.lower().endswith('.jpg')]
        if photos:
            print("Verifying metadata in current directory photos...")
            for photo in photos:
                metadata = read_metadata_from_photo(photo)
                print(f"{photo}: {metadata}")
        else:
            print("No JPEG photos found in current directory")
    else:
        test_rapid_navigation_preserves_metadata()
