# Photo Metadata Editor

A desktop application for editing metadata of scanned photos with Apple Photos compatibility. Perfect for organizing and adding metadata to digitized photo collections.

## Features

- **Photo Browsing**: View JPEG photos from selected folders with smooth navigation
- **Keyboard Navigation**: Use arrow keys to quickly move between photos
- **Smart Date Input**: Enter dates in natural language (e.g., "jan 1 2001", "5/11/01", "2001")
- **Caption Management**: Add descriptions that appear in Apple Photos
- **Location Geocoding**: Type location names to automatically add GPS coordinates
- **Auto-Save**: All changes are automatically saved to EXIF data
- **Apple Photos Compatible**: Metadata fields work seamlessly with Apple Photos
- **Batch Processing**: Copy metadata between photos for efficient batch editing
- **Safe Editing**: Automatic backup files created before modifying originals

## Requirements

- Python 3.8 or higher
- macOS, Windows, or Linux

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python photo_metadata_editor_qt.py
```

### Getting Started
1. Click "Select Folder" or press `Ctrl+O` to choose a folder containing JPEG photos
2. Use left/right arrow keys to navigate between photos
3. Edit metadata in the right panel:
   - **Date**: Enter in natural language (automatically parsed and formatted)
   - **Caption**: Add photo descriptions
   - **Location**: Type location names for automatic GPS coordinate lookup
4. All changes are saved automatically to EXIF data
5. Use "Copy from Previous Photo" to batch-apply metadata

### Keyboard Shortcuts
- `←` `→` - Navigate between photos
- `Ctrl+O` - Open folder selection dialog
- `Esc` - Hide location suggestions

## Dependencies

- **PySide6**: Modern Qt-based GUI framework
- **Pillow**: Image processing and EXIF handling
- **geopy**: Geocoding for location suggestions
- **python-dateutil**: Natural language date parsing
- **piexif**: Advanced EXIF data manipulation
- **requests**: HTTP requests for geocoding API

## Supported File Formats

- JPEG files (.jpg, .jpeg)
- Files with existing EXIF data (recommended)
- Recursive folder scanning supported

## Metadata Compatibility

This application writes metadata in formats compatible with:
- **Apple Photos** (primary target)
- **Adobe Lightroom**
- **Google Photos**
- **Most photo management applications**

### EXIF Fields Used
- `DateTimeOriginal` - Photo date/time
- `ImageDescription` - Photo caption/description
- `GPS` fields - Location coordinates
- `UserComment` - Additional caption storage

## Tips for Best Results

1. **Date Input**: Use natural language for easy date entry:
   - "2001" → January 1, 2001
   - "jan 15 2001" → January 15, 2001
   - "5/11/01" → May 11, 2001

2. **Location Input**: Be specific for better geocoding results:
   - "Paris, France" instead of just "Paris"
   - "Central Park, New York" instead of just "park"

3. **Batch Processing**: Use "Copy from Previous Photo" to quickly apply the same metadata to multiple photos from the same event or location

4. **Backup Safety**: The application automatically creates `.backup` files before modifying originals. These can be used to restore if needed.

## Troubleshooting

### Common Issues

**No photos appear after selecting folder:**
- Ensure the folder contains JPEG files (.jpg or .jpeg extensions)
- Check that files are not corrupted

**Location suggestions not working:**
- Verify internet connection
- Try more specific location names
- Some locations may not be found in the geocoding database

**Metadata not appearing in Apple Photos:**
- Ensure you're using JPEG files (not HEIC or other formats)
- Try reimporting photos into Apple Photos after editing
- Some metadata may take time to appear in Apple Photos

### Getting Help

If you encounter issues:
1. Check that all dependencies are installed correctly
2. Verify your Python version is 3.8 or higher
3. Ensure you have write permissions to the photo folder
4. Check the application's status bar for error messages

## License

This project is open source. Feel free to modify and distribute according to your needs.
