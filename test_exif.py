#!/usr/bin/env python3
"""
Test script to verify EXIF metadata functionality
"""

import os
import piexif
from PIL import Image
from datetime import datetime

def create_test_image(filename, width=800, height=600):
    """Create a test JPEG image."""
    # Create a simple test image
    img = Image.new('RGB', (width, height), color='lightblue')
    
    # Add some basic EXIF data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "Test Camera",
            piexif.ImageIFD.Model: "Test Model",
            piexif.ImageIFD.DateTime: "2020:01:01 12:00:00",
            piexif.ImageIFD.ImageDescription: "Test photo description"
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: "2020:01:01 12:00:00"
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitude: [(40, 1), (0, 1), (0, 1)],
            piexif.GPSIFD.GPSLatitudeRef: 'N',
            piexif.GPSIFD.GPSLongitude: [(105, 1), (0, 1), (0, 1)],
            piexif.GPSIFD.GPSLongitudeRef: 'W'
        },
        "1st": {},
        "thumbnail": None
    }
    
    exif_bytes = piexif.dump(exif_dict)
    img.save(filename, "JPEG", exif=exif_bytes)
    print(f"Created test image: {filename}")

def test_exif_reading(filename):
    """Test reading EXIF data from an image."""
    try:
        exif_dict = piexif.load(filename)
        print(f"\nEXIF data for {filename}:")
        
        # Test date reading
        if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
            print(f"  Date: {date_str}")
        
        # Test description reading
        if "0th" in exif_dict and piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
            desc = exif_dict["0th"][piexif.ImageIFD.ImageDescription].decode('utf-8')
            print(f"  Description: {desc}")
        
        # Test GPS reading
        if "GPS" in exif_dict:
            print("  GPS data found")
            
        return True
    except Exception as e:
        print(f"Error reading EXIF from {filename}: {e}")
        return False

def main():
    """Main test function."""
    # Create test images directory
    test_dir = "test_photos"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Create test images
    test_files = [
        "test_photo_1.jpg",
        "test_photo_2.jpg", 
        "test_photo_3.jpg"
    ]
    
    for i, filename in enumerate(test_files):
        filepath = os.path.join(test_dir, filename)
        create_test_image(filepath, 800 + i*100, 600 + i*50)
        test_exif_reading(filepath)
    
    print(f"\nTest photos created in '{test_dir}' directory")
    print("You can now test the Photo Metadata Editor with these files!")

if __name__ == "__main__":
    main()
