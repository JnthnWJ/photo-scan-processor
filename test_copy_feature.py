#!/usr/bin/env python3
"""
Test script for the Copy from Previous feature in Photo Metadata Editor
"""

import os
import sys
import tempfile
import shutil
from PIL import Image
import piexif
from datetime import datetime

def create_test_images():
    """Create test JPEG images with some metadata."""
    test_dir = tempfile.mkdtemp(prefix="photo_test_")
    print(f"Creating test images in: {test_dir}")
    
    # Create two test images
    for i in range(1, 3):
        # Create a simple image
        img = Image.new('RGB', (800, 600), color=(100 + i * 50, 150, 200))
        
        # Add some basic EXIF data to the first image
        if i == 1:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # Add date
            date_str = "2023:06:15 14:30:00"
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
            exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
            
            # Add caption
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = "Test photo with metadata"
            
            # Add GPS coordinates (Boulder, CO approximately)
            lat_deg, lat_min, lat_sec = 40, 0, 0
            lon_deg, lon_min, lon_sec = 105, 16, 0
            
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [(lat_deg, 1), (lat_min, 1), (lat_sec, 1)]
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N'
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [(lon_deg, 1), (lon_min, 1), (lon_sec, 1)]
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'W'
            
            # Save with EXIF
            exif_bytes = piexif.dump(exif_dict)
            img_path = os.path.join(test_dir, f"test_photo_{i}.jpg")
            img.save(img_path, "JPEG", exif=exif_bytes)
        else:
            # Save without EXIF
            img_path = os.path.join(test_dir, f"test_photo_{i}.jpg")
            img.save(img_path, "JPEG")
    
    print(f"Created test images:")
    for file in os.listdir(test_dir):
        if file.endswith('.jpg'):
            print(f"  - {file}")
    
    return test_dir

def main():
    """Main test function."""
    print("Testing Copy from Previous feature...")
    
    # Create test images
    test_dir = create_test_images()
    
    print(f"\nTest setup complete!")
    print(f"Test directory: {test_dir}")
    print("\nTo test the Copy from Previous feature:")
    print("1. Run the photo metadata editor")
    print("2. Select the test folder created above")
    print("3. Navigate to the first photo (should have metadata)")
    print("4. Navigate to the second photo (should be empty)")
    print("5. Click 'Copy from Previous Photo' button")
    print("6. Verify that date, caption, and location are copied")
    
    # Keep the directory for manual testing
    print(f"\nTest directory will remain at: {test_dir}")
    print("Delete it manually when done testing.")

if __name__ == "__main__":
    main()
