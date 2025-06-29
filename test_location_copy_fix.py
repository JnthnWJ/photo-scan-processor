#!/usr/bin/env python3
"""
Test script to verify the location copying fix works correctly.
This script tests the metadata copying functionality without requiring the full GUI.
"""

import os
import sys
import tempfile
import shutil
from PIL import Image
import piexif
from datetime import datetime

# Add the current directory to the path so we can import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_image_with_metadata(path, location_data=None, caption=None, date=None):
    """Create a test JPEG image with metadata."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Create EXIF data
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # Add date if provided
    if date:
        date_str = date.strftime("%Y:%m:%d %H:%M:%S")
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
    
    # Add caption if provided
    if caption:
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = caption.encode('utf-8')
    
    # Add location if provided
    if location_data:
        if 'latitude' in location_data and 'longitude' in location_data and location_data['latitude'] is not None:
            # Add GPS coordinates
            lat = location_data['latitude']
            lon = location_data['longitude']
            
            # Convert to GPS format
            lat_deg = int(abs(lat))
            lat_min = int((abs(lat) - lat_deg) * 60)
            lat_sec = int(((abs(lat) - lat_deg) * 60 - lat_min) * 60 * 1000)
            
            lon_deg = int(abs(lon))
            lon_min = int((abs(lon) - lon_deg) * 60)
            lon_sec = int(((abs(lon) - lon_deg) * 60 - lon_min) * 60 * 1000)
            
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [(lat_deg, 1), (lat_min, 1), (lat_sec, 1000)]
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [(lon_deg, 1), (lon_min, 1), (lon_sec, 1000)]
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'
        elif 'address' in location_data:
            # Add text-only location
            exif_dict["GPS"][piexif.GPSIFD.GPSProcessingMethod] = location_data['address'].encode('utf-8')
    
    # Save image with EXIF
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, "JPEG", exif=exif_bytes)

def read_location_from_exif(path):
    """Read location data from EXIF."""
    try:
        exif_dict = piexif.load(path)
        gps_info = exif_dict.get("GPS", {})
        
        # Check for GPS coordinates
        if piexif.GPSIFD.GPSLatitude in gps_info and piexif.GPSIFD.GPSLongitude in gps_info:
            lat_data = gps_info[piexif.GPSIFD.GPSLatitude]
            lat_ref = gps_info[piexif.GPSIFD.GPSLatitudeRef]
            lon_data = gps_info[piexif.GPSIFD.GPSLongitude]
            lon_ref = gps_info[piexif.GPSIFD.GPSLongitudeRef]
            
            # Convert to decimal
            lat = lat_data[0][0]/lat_data[0][1] + lat_data[1][0]/lat_data[1][1]/60 + lat_data[2][0]/lat_data[2][1]/3600
            lon = lon_data[0][0]/lon_data[0][1] + lon_data[1][0]/lon_data[1][1]/60 + lon_data[2][0]/lon_data[2][1]/3600
            
            if lat_ref.decode('utf-8') == 'S':
                lat = -lat
            if lon_ref.decode('utf-8') == 'W':
                lon = -lon
                
            return {'latitude': lat, 'longitude': lon, 'type': 'coordinates'}
        
        # Check for text-only location
        if piexif.GPSIFD.GPSProcessingMethod in gps_info:
            address = gps_info[piexif.GPSIFD.GPSProcessingMethod].decode('utf-8')
            return {'address': address, 'type': 'text'}
            
        return None
    except Exception as e:
        print(f"Error reading EXIF: {e}")
        return None

def test_location_copying():
    """Test the location copying functionality."""
    print("Testing location copying fix...")
    
    # Create temporary directory for test images
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test case 1: Copy location with coordinates
        print("\n1. Testing copy with GPS coordinates...")
        
        photo1_path = os.path.join(temp_dir, "photo1.jpg")
        photo2_path = os.path.join(temp_dir, "photo2.jpg")
        
        # Create first photo with GPS coordinates
        location_with_coords = {
            'address': 'Boulder, Colorado',
            'latitude': 40.0150,
            'longitude': -105.2705
        }
        create_test_image_with_metadata(photo1_path, location_data=location_with_coords)
        
        # Create second photo without location
        create_test_image_with_metadata(photo2_path)
        
        # Simulate the copying process
        from photo_metadata_editor import PhotoMetadataEditor
        
        # Create app instance (but don't run GUI)
        app = PhotoMetadataEditor()
        app.photo_files = [photo1_path, photo2_path]
        app.current_photo_index = 0
        
        # Load first photo and store its metadata
        app.load_current_photo()
        app.store_current_metadata()
        
        # Switch to second photo
        app.current_photo_index = 1
        app.load_current_photo()
        
        # Copy metadata from previous photo
        app.copy_from_previous_photo()
        
        # Check if location was saved to second photo
        saved_location = read_location_from_exif(photo2_path)
        if saved_location and saved_location.get('type') == 'coordinates':
            print("✓ GPS coordinates copied successfully")
            print(f"  Latitude: {saved_location['latitude']:.4f}")
            print(f"  Longitude: {saved_location['longitude']:.4f}")
        else:
            print("✗ GPS coordinates copy failed")
            return False
        
        # Test case 2: Copy text-only location
        print("\n2. Testing copy with text-only location...")
        
        photo3_path = os.path.join(temp_dir, "photo3.jpg")
        photo4_path = os.path.join(temp_dir, "photo4.jpg")
        
        # Create third photo with text-only location
        location_text_only = {'address': 'Denver, Colorado'}
        create_test_image_with_metadata(photo3_path, location_data=location_text_only)
        
        # Create fourth photo without location
        create_test_image_with_metadata(photo4_path)
        
        # Update app with new photos
        app.photo_files = [photo3_path, photo4_path]
        app.current_photo_index = 0
        
        # Load third photo and store its metadata
        app.load_current_photo()
        app.store_current_metadata()
        
        # Switch to fourth photo
        app.current_photo_index = 1
        app.load_current_photo()
        
        # Copy metadata from previous photo
        app.copy_from_previous_photo()
        
        # Check if text location was saved to fourth photo
        saved_location = read_location_from_exif(photo4_path)
        if saved_location and saved_location.get('type') == 'text':
            print("✓ Text-only location copied successfully")
            print(f"  Address: {saved_location['address']}")
        else:
            print("✗ Text-only location copy failed")
            return False
        
        print("\n✓ All location copying tests passed!")
        return True

if __name__ == "__main__":
    success = test_location_copying()
    sys.exit(0 if success else 1)
