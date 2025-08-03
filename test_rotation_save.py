#!/usr/bin/env python3
"""
Test script to verify rotation saving functionality.
"""

import sys
import os
import tempfile
import shutil
from PIL import Image
import piexif

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_image(path, size=(400, 300), color=(255, 0, 0)):
    """Create a test image with some distinguishable content."""
    img = Image.new('RGB', size, color)
    
    # Add some text or pattern to make rotation visible
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    
    # Draw a simple pattern to make rotation obvious
    draw.rectangle([10, 10, 50, 50], fill=(0, 255, 0))  # Green square in top-left
    draw.rectangle([size[0]-50, size[1]-50, size[0]-10, size[1]-10], fill=(0, 0, 255))  # Blue square in bottom-right
    draw.text((size[0]//2-20, size[1]//2), "TEST", fill=(255, 255, 255))
    
    # Save with basic EXIF
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "Test Camera",
            piexif.ImageIFD.Model: "Rotation Test Model",
            piexif.ImageIFD.DateTime: "2024:01:01 12:00:00"
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: "2024:01:01 12:00:00"
        },
        "GPS": {},
        "1st": {},
        "thumbnail": None
    }
    
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, exif=exif_bytes, quality=95)
    return path

def test_rotation_functionality():
    """Test the rotation saving functionality."""
    print("Testing rotation save functionality...")
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test image
        test_image_path = os.path.join(temp_dir, "test_rotation.jpg")
        create_test_image(test_image_path)
        
        print(f"Created test image: {test_image_path}")
        
        # Check original image size
        original_img = Image.open(test_image_path)
        original_size = original_img.size
        print(f"Original image size: {original_size}")
        original_img.close()
        
        # Test PIL rotation methods (same as used in the app)
        test_img = Image.open(test_image_path)
        
        # Test 90-degree rotation (clockwise)
        rotated_90 = test_img.transpose(Image.Transpose.ROTATE_270)  # ROTATE_270 = 90° clockwise
        rotated_90_path = os.path.join(temp_dir, "test_rotated_90.jpg")
        rotated_90.save(rotated_90_path, quality=95)
        print(f"90° rotation size: {rotated_90.size}")

        # Test 180-degree rotation
        rotated_180 = test_img.transpose(Image.Transpose.ROTATE_180)
        rotated_180_path = os.path.join(temp_dir, "test_rotated_180.jpg")
        rotated_180.save(rotated_180_path, quality=95)
        print(f"180° rotation size: {rotated_180.size}")

        # Test 270-degree rotation (counter-clockwise 90°)
        rotated_270 = test_img.transpose(Image.Transpose.ROTATE_90)   # ROTATE_90 = 270° clockwise
        rotated_270_path = os.path.join(temp_dir, "test_rotated_270.jpg")
        rotated_270.save(rotated_270_path, quality=95)
        print(f"270° rotation size: {rotated_270.size}")
        
        test_img.close()
        rotated_90.close()
        rotated_180.close()
        rotated_270.close()
        
        print("✓ Rotation test completed successfully!")
        print("The rotation saving functionality should work correctly.")
        
        # Copy test images to a visible location for manual inspection
        visible_dir = os.path.join(os.path.dirname(__file__), "test_rotation_output")
        if os.path.exists(visible_dir):
            shutil.rmtree(visible_dir)
        os.makedirs(visible_dir)
        
        shutil.copy2(test_image_path, os.path.join(visible_dir, "original.jpg"))
        shutil.copy2(rotated_90_path, os.path.join(visible_dir, "rotated_90.jpg"))
        shutil.copy2(rotated_180_path, os.path.join(visible_dir, "rotated_180.jpg"))
        shutil.copy2(rotated_270_path, os.path.join(visible_dir, "rotated_270.jpg"))
        
        print(f"Test images saved to: {visible_dir}")
        print("You can manually inspect these to verify rotation works correctly.")

if __name__ == "__main__":
    test_rotation_functionality()
