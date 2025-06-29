# Photo Metadata Editor

A desktop application for editing metadata of scanned photos with Apple Photos compatibility.

## Features

- Browse and view JPEG photos from selected folders
- Navigate photos with keyboard arrow keys
- Edit metadata in real-time:
  - Natural language date input
  - Photo captions/descriptions
  - Location with geocoding suggestions
- Auto-save metadata to EXIF data
- Apple Photos compatible metadata fields

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python photo_metadata_editor.py
```

1. Click "Select Folder" to choose a folder containing JPEG photos
2. Use left/right arrow keys to navigate between photos
3. Edit metadata in the right panel - changes are saved automatically
4. Metadata is written directly to EXIF data for Apple Photos compatibility

## Dependencies

- **Pillow**: Image processing and EXIF handling
- **customtkinter**: Modern GUI framework
- **geopy**: Geocoding for location suggestions
- **python-dateutil**: Natural language date parsing
- **piexif**: Advanced EXIF data manipulation
- **requests**: HTTP requests for geocoding API
