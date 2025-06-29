# Photo Metadata Editor - Usage Guide

## Quick Start

1. **Launch the Application**
   ```bash
   python photo_metadata_editor.py
   ```

2. **Select a Photo Folder**
   - Click "Select Folder" button or press `Ctrl+O`
   - Choose a folder containing JPEG photos
   - The application will scan for all JPEG files in the folder

3. **Navigate Photos**
   - Use left/right arrow keys to move between photos
   - Current photo information is displayed in the metadata panel

4. **Edit Metadata**
   - **Date Field**: Enter dates naturally (examples below)
   - **Caption Field**: Add descriptions for your photos
   - **Location Field**: Type location names for GPS coordinates

## Date Field Examples

The date field accepts natural language input and automatically formats dates for EXIF compatibility:

- `2001` → January 1, 2001
- `5/11/01` → May 11, 2001
- `jan 1 2001` → January 1, 2001
- `December 25, 1995` → December 25, 1995
- `1995-12-25` → December 25, 1995

## Location Field Features

- **Real-time Suggestions**: As you type, the application provides location suggestions
- **GPS Coordinates**: Selected locations are automatically converted to GPS coordinates
- **EXIF Compatibility**: GPS data is written to standard EXIF fields
- **Examples**: "Boulder, Colorado", "Paris, France", "123 Main St, Denver, CO"

## Caption/Description Field

- Supports multi-line text descriptions
- Written to EXIF ImageDescription field (compatible with Apple Photos)
- Also written to UserComment field for additional compatibility

## Auto-Save Features

- **Real-time Saving**: Changes are automatically saved as you type
- **No Save Button**: No manual save action required
- **Backup Creation**: Original files are backed up before modification
- **Visual Feedback**: Green checkmark appears when changes are saved

## Keyboard Shortcuts

- `←` / `→` : Navigate between photos
- `Ctrl+O` : Open folder selection dialog
- `Esc` : Hide location suggestions dropdown

## Apple Photos Compatibility

The application writes metadata to EXIF fields that Apple Photos recognizes:

- **Dates**: Written to DateTimeOriginal, DateTime, and ImageIFD.DateTime
- **Descriptions**: Written to ImageDescription and UserComment
- **GPS**: Written to standard GPS EXIF fields (GPSLatitude, GPSLongitude, etc.)

## File Safety

- **Backup Files**: Original files are backed up with `.backup` extension
- **EXIF Preservation**: Existing EXIF data is preserved when adding new metadata
- **Error Handling**: Robust error handling prevents file corruption

## Troubleshooting

### No Photos Found
- Ensure the folder contains JPEG files (.jpg or .jpeg extensions)
- Check that files are valid JPEG images

### Location Suggestions Not Working
- Check internet connection (required for geocoding)
- Try more specific location names
- Use format: "City, State" or "City, Country"

### Metadata Not Saving
- Ensure you have write permissions to the photo folder
- Check that the photo file is not read-only
- Look for error messages in the status bar

### Application Won't Start
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.8+ required)

## Technical Details

### Supported Formats
- JPEG files with EXIF data
- Both .jpg and .jpeg extensions
- RGB and grayscale images

### EXIF Fields Used
- **Date**: DateTimeOriginal, DateTime, ImageIFD.DateTime
- **Caption**: ImageDescription, UserComment
- **GPS**: GPSLatitude, GPSLongitude, GPSLatitudeRef, GPSLongitudeRef

### Dependencies
- **Pillow**: Image processing and basic EXIF handling
- **piexif**: Advanced EXIF data manipulation
- **PySide6**: Modern Qt-based GUI framework
- **geopy**: Geocoding services
- **python-dateutil**: Natural language date parsing
- **requests**: HTTP requests for geocoding API

## Tips for Batch Processing

1. **Organize by Date**: Use consistent date formats for easier sorting
2. **Location Shortcuts**: Save frequently used locations in a text file for copy/paste
3. **Caption Templates**: Develop standard caption formats for different photo types
4. **Backup Strategy**: Keep original backups in a separate location
5. **Apple Photos Import**: After editing, import photos to Apple Photos to verify metadata

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all dependencies are properly installed
3. Test with the included sample photos in `test_photos/` directory
