#!/usr/bin/env python3
"""
Photo Metadata Editor - PySide6 Version
A desktop application for editing metadata of scanned photos with Apple Photos compatibility.
"""

import os
import sys
from typing import List, Optional, Dict, Any
from collections import OrderedDict
import threading
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QScrollArea, QFrame,
    QFileDialog, QMessageBox, QStatusBar, QToolBar, QSplitter,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize, QEvent, QRectF
from PySide6.QtGui import QPixmap, QFont, QKeySequence, QShortcut, QAction, QImage, QWheelEvent, QPainter

from PIL import Image
import piexif
from datetime import datetime
from dateutil import parser as date_parser
from geopy.geocoders import Nominatim
import requests


class ZoomableImageViewer(QGraphicsView):
    """A zoomable and pannable image viewer widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create graphics scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Image item
        self.image_item = None

        # Zoom settings
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 1.2

        # Configure view
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameStyle(QFrame.NoFrame)

        # Enable mouse tracking for panning
        self.setMouseTracking(True)

        # Initial state
        self.has_image = False
        self.fit_to_window_on_load = True

    def set_image(self, pixmap: QPixmap):
        """Set the image to display."""
        # Clear existing image
        if self.image_item:
            self.scene.removeItem(self.image_item)

        # Add new image
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)

        # Update scene rect to match image
        self.scene.setSceneRect(self.image_item.boundingRect())

        # Fit to window by default
        if self.fit_to_window_on_load:
            self.fit_to_window()

        self.has_image = True

    def fit_to_window(self):
        """Fit the image to the window size."""
        if not self.image_item:
            return

        # Get the view's viewport size
        view_rect = self.viewport().rect()

        # Get the image's bounding rect
        image_rect = self.image_item.boundingRect()

        if image_rect.isEmpty() or view_rect.isEmpty():
            return

        # Calculate scale to fit image in view
        scale_x = view_rect.width() / image_rect.width()
        scale_y = view_rect.height() / image_rect.height()
        scale = min(scale_x, scale_y)

        # Apply the scale
        self.resetTransform()
        self.scale(scale, scale)
        self.zoom_factor = scale

        # Center the image
        self.centerOn(self.image_item)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming."""
        if not self.has_image:
            return

        # Get the position of the mouse in scene coordinates
        scene_pos = self.mapToScene(event.position().toPoint())

        # Calculate zoom
        if event.angleDelta().y() > 0:
            zoom_in = True
            factor = self.zoom_step
        else:
            zoom_in = False
            factor = 1.0 / self.zoom_step

        # Check zoom limits
        new_zoom = self.zoom_factor * factor
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        # Apply zoom
        self.scale(factor, factor)
        self.zoom_factor = new_zoom

        # Keep the mouse position fixed during zoom
        new_scene_pos = self.mapToScene(event.position().toPoint())
        delta = new_scene_pos - scene_pos
        self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MiddleButton:
            # Middle click to fit to window
            self.fit_to_window()
        elif event.button() == Qt.LeftButton and self.has_image:
            # Left click to pan
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        if self.has_image and self.fit_to_window_on_load:
            # Re-fit to window when resized
            QTimer.singleShot(100, self.fit_to_window)

    def reset_zoom(self):
        """Reset zoom to fit window."""
        self.fit_to_window()

    def zoom_in(self):
        """Zoom in."""
        if not self.has_image:
            return
        factor = self.zoom_step
        new_zoom = self.zoom_factor * factor
        if new_zoom <= self.max_zoom:
            self.scale(factor, factor)
            self.zoom_factor = new_zoom

    def zoom_out(self):
        """Zoom out."""
        if not self.has_image:
            return
        factor = 1.0 / self.zoom_step
        new_zoom = self.zoom_factor * factor
        if new_zoom >= self.min_zoom:
            self.scale(factor, factor)
            self.zoom_factor = new_zoom


class PhotoMetadataEditor(QMainWindow):
    """Main application class for the Photo Metadata Editor."""
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        # Application state
        self.current_folder = None
        self.photo_files = []
        self.current_photo_index = 0
        self.current_image = None
        self.current_pixmap = None
        
        # Image caching system
        self.image_cache = OrderedDict()  # LRU cache for original images
        self.scaled_cache = OrderedDict()  # LRU cache for scaled images
        self.max_cache_size = 10  # Cache up to 10 images
        self.max_scaled_cache_size = 20  # Cache more scaled versions
        
        # Auto-save system
        self.pending_changes = {}
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.save_pending_metadata)

        # Navigation debouncing
        self._navigation_pending = False
        self._last_navigation_time = 0
        self._navigation_debounce_ms = 50  # 50ms debounce
        self._pending_direction = None
        self._navigation_timer = QTimer()
        self._navigation_timer.setSingleShot(True)
        self._navigation_timer.timeout.connect(self._execute_navigation)

        # Metadata loading state
        self._metadata_loaded = False
        
        # Geocoder for location suggestions
        print(f"[DEBUG] Initializing Nominatim geocoder...")
        try:
            self.geocoder = Nominatim(user_agent="photo_metadata_editor")
            print(f"[DEBUG] Geocoder initialized successfully: {self.geocoder}")
        except Exception as e:
            print(f"[DEBUG] Failed to initialize geocoder: {e}")
            self.geocoder = None
            
        # Location suggestions state
        self.location_suggestions = []
        self.highlighted_suggestion_index = -1
        self._last_selected_location = None
        self.previous_photo_metadata = {}
        
        # Geocoding state
        self._geocoding_results_ready = False
        self._pending_locations = None
        self._polling_active = False
        
        # Initialize UI
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        
        # Set window properties
        self.setWindowTitle("Photo Metadata Editor")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
    def setup_ui(self):
        """Set up the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal)
        central_widget_layout = QVBoxLayout(central_widget)
        central_widget_layout.addWidget(main_splitter)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create photo viewer (left side)
        self.create_photo_viewer(main_splitter)
        
        # Create metadata panel (right side)
        self.create_metadata_panel(main_splitter)
        
        # Set splitter proportions (2:1 ratio)
        main_splitter.setSizes([800, 400])
        
        # Create status bar
        self.create_status_bar()

        # Show placeholder initially
        self.show_placeholder()
        
    def create_toolbar(self):
        """Create the top toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Select folder action
        select_folder_action = QAction("Select Folder", self)
        select_folder_action.triggered.connect(self.select_folder)
        toolbar.addAction(select_folder_action)
        
        toolbar.addSeparator()
        
        # Help action
        help_action = QAction("Help", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
        
        toolbar.addSeparator()
        
        # Folder path label
        self.folder_path_label = QLabel("No folder selected - Press Cmd+O or click 'Select Folder'")
        self.folder_path_label.setStyleSheet("QLabel { margin-left: 10px; }")
        toolbar.addWidget(self.folder_path_label)
        
    def create_photo_viewer(self, parent):
        """Create the photo viewer area."""
        # Create photo viewer frame
        self.photo_frame = QFrame()
        self.photo_frame.setFrameStyle(QFrame.StyledPanel)
        parent.addWidget(self.photo_frame)

        # Layout for photo viewer
        photo_layout = QVBoxLayout(self.photo_frame)

        # Photo display viewer (zoomable)
        self.photo_viewer = ZoomableImageViewer()
        self.photo_viewer.setMinimumSize(400, 300)
        photo_layout.addWidget(self.photo_viewer)

        # Placeholder label for when no image is loaded
        self.placeholder_label = QLabel("Select a folder to view photos")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("QLabel { font-size: 16px; }")
        self.placeholder_label.hide()  # Initially hidden, will show when needed
        photo_layout.addWidget(self.placeholder_label)

        # Navigation info
        self.nav_info_label = QLabel("Use ← → arrow keys to navigate | Mouse wheel to zoom | Middle click to fit")
        self.nav_info_label.setAlignment(Qt.AlignCenter)
        self.nav_info_label.setStyleSheet("QLabel { font-size: 12px; color: gray; }")
        photo_layout.addWidget(self.nav_info_label)
        
    def create_metadata_panel(self, parent):
        """Create the metadata editing panel."""
        # Create metadata frame
        self.metadata_frame = QFrame()
        self.metadata_frame.setFrameStyle(QFrame.StyledPanel)
        parent.addWidget(self.metadata_frame)
        
        # Main layout for metadata panel
        metadata_layout = QVBoxLayout(self.metadata_frame)
        
        # Create scrollable area for metadata fields
        self.metadata_scroll = QScrollArea()
        self.metadata_scroll.setWidgetResizable(True)
        self.metadata_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        metadata_layout.addWidget(self.metadata_scroll)
        
        # Create content widget for scroll area
        self.metadata_content = QWidget()
        self.metadata_scroll.setWidget(self.metadata_content)
        
        # Layout for metadata content
        self.metadata_content_layout = QVBoxLayout(self.metadata_content)
        
        # Title
        title_label = QLabel("Photo Metadata")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        self.metadata_content_layout.addWidget(title_label)
        
        # Current photo info
        self.photo_info_frame = QFrame()
        self.photo_info_frame.setFrameStyle(QFrame.StyledPanel)
        self.metadata_content_layout.addWidget(self.photo_info_frame)
        
        photo_info_layout = QVBoxLayout(self.photo_info_frame)
        self.photo_info_label = QLabel("No photo selected")
        self.photo_info_label.setWordWrap(True)
        photo_info_layout.addWidget(self.photo_info_label)
        
        # Create metadata input fields
        self.create_date_field()
        self.create_caption_field()
        self.create_location_field()
        self.create_copy_from_previous_button()
        
        # Auto-save status
        self.autosave_label = QLabel("Changes are saved automatically")
        self.autosave_label.setStyleSheet("QLabel { font-size: 10px; color: gray; }")
        self.metadata_content_layout.addWidget(self.autosave_label)
        
        # Add stretch to push everything to the top
        self.metadata_content_layout.addStretch()
        
    def create_date_field(self):
        """Create the date input field."""
        # Date field frame
        date_frame = QFrame()
        date_frame.setFrameStyle(QFrame.StyledPanel)
        self.metadata_content_layout.addWidget(date_frame)
        
        date_layout = QVBoxLayout(date_frame)
        
        # Date label
        date_label = QLabel("Date:")
        date_font = QFont()
        date_font.setBold(True)
        date_label.setFont(date_font)
        date_layout.addWidget(date_label)
        
        # Date entry
        self.date_entry = QLineEdit()
        self.date_entry.setPlaceholderText("Enter date (e.g., '2001', 'jan 1 2001', '5/11/01')")
        self.date_entry.textChanged.connect(self.on_date_change)
        # Install event filter to handle Tab, Enter, and focus events
        self.date_entry.installEventFilter(self)
        date_layout.addWidget(self.date_entry)

        # Date suggestions frame (initially hidden)
        self.date_suggestions_frame = QFrame()
        self.date_suggestions_layout = QVBoxLayout(self.date_suggestions_frame)
        self.date_suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self.date_suggestions_frame.hide()
        date_layout.addWidget(self.date_suggestions_frame)
        
        # Date hint
        date_hint = QLabel("Natural language dates supported (e.g., 'jan 1 2001', '5/11/01')")
        date_hint.setStyleSheet("QLabel { font-size: 10px; color: gray; }")
        date_hint.setWordWrap(True)
        date_layout.addWidget(date_hint)
        
    def create_caption_field(self):
        """Create the caption/description field."""
        # Caption field frame
        caption_frame = QFrame()
        caption_frame.setFrameStyle(QFrame.StyledPanel)
        self.metadata_content_layout.addWidget(caption_frame)
        
        caption_layout = QVBoxLayout(caption_frame)
        
        # Caption label
        caption_label = QLabel("Caption/Description:")
        caption_font = QFont()
        caption_font.setBold(True)
        caption_label.setFont(caption_font)
        caption_layout.addWidget(caption_label)
        
        # Caption text area
        self.caption_text = QTextEdit()
        self.caption_text.setMaximumHeight(100)
        self.caption_text.setPlaceholderText("Enter photo description...")
        self.caption_text.textChanged.connect(self.on_caption_change)
        caption_layout.addWidget(self.caption_text)
        
        # Caption hint
        caption_hint = QLabel("Description will be visible in Apple Photos")
        caption_hint.setStyleSheet("QLabel { font-size: 10px; color: gray; }")
        caption_layout.addWidget(caption_hint)
        
    def create_location_field(self):
        """Create the location input field."""
        # Location field frame
        location_frame = QFrame()
        location_frame.setFrameStyle(QFrame.StyledPanel)
        self.metadata_content_layout.addWidget(location_frame)
        
        location_layout = QVBoxLayout(location_frame)
        
        # Location label
        location_label = QLabel("Location:")
        location_font = QFont()
        location_font.setBold(True)
        location_label.setFont(location_font)
        location_layout.addWidget(location_label)
        
        # Location entry
        self.location_entry = QLineEdit()
        self.location_entry.setPlaceholderText("Enter location name...")
        self.location_entry.textChanged.connect(self.on_location_change)
        location_layout.addWidget(self.location_entry)
        
        # Location suggestions frame (initially hidden)
        self.location_suggestions_frame = QFrame()
        self.location_suggestions_layout = QVBoxLayout(self.location_suggestions_frame)
        self.location_suggestions_frame.hide()
        location_layout.addWidget(self.location_suggestions_frame)
        
        # Location hint
        location_hint = QLabel("GPS coordinates will be added automatically")
        location_hint.setStyleSheet("QLabel { font-size: 10px; color: gray; }")
        location_layout.addWidget(location_hint)
        
    def create_copy_from_previous_button(self):
        """Create the copy from previous photo button."""
        self.copy_from_previous_btn = QPushButton("Copy from Previous Photo")
        self.copy_from_previous_btn.setEnabled(False)
        self.copy_from_previous_btn.clicked.connect(self.copy_from_previous_photo)
        self.metadata_content_layout.addWidget(self.copy_from_previous_btn)
        
        # Copy hint
        self.copy_hint_label = QLabel("No previous photo metadata available")
        self.copy_hint_label.setStyleSheet("QLabel { font-size: 10px; color: gray; }")
        self.metadata_content_layout.addWidget(self.copy_hint_label)
        
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Navigation shortcuts
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.left_shortcut.activated.connect(self.previous_photo)

        self.right_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.right_shortcut.activated.connect(self.next_photo)

        # File operations
        self.open_shortcut = QShortcut(QKeySequence.Open, self)
        self.open_shortcut.activated.connect(self.select_folder)

        # Hide suggestions
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.escape_shortcut.activated.connect(self.hide_all_suggestions)

    def show_help(self):
        """Show help dialog."""
        help_text = """PHOTO METADATA EDITOR - HELP

NAVIGATION:
• Use ← → arrow keys to navigate between photos
• Click 'Select Folder' or press Cmd+O to choose a photo folder

METADATA EDITING:
• Date: Enter dates in natural language (e.g., "2001", "5/11/01", "jan 1 2001")
• Caption: Add descriptions that will appear in Apple Photos
• Location: Type location names for GPS coordinates and suggestions
• Copy from Previous: Click to copy all metadata from the previously viewed photo

FEATURES:
• All changes are saved automatically to EXIF data
• Metadata is compatible with Apple Photos
• GPS coordinates are added for location entries
• Supports JPEG files with EXIF data
• Copy metadata between photos for batch processing

KEYBOARD SHORTCUTS:
• Cmd+O: Open folder
• ← →: Navigate photos
• Esc: Hide location suggestions

The application creates backup files (.backup) before modifying originals."""

        QMessageBox.information(self, "Help - Photo Metadata Editor", help_text)

    def select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select folder containing photos")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder_path: str):
        """Load photos from the selected folder."""
        try:
            # Clear caches when loading new folder
            self._clear_image_caches()

            self.current_folder = folder_path
            self.folder_path_label.setText(f"Folder: {os.path.basename(folder_path)}")

            # Find JPEG files recursively with lightweight validation
            self.photo_files = []
            supported_extensions = ('.jpg', '.jpeg', '.JPG', '.JPEG')

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(supported_extensions):
                        full_path = os.path.join(root, file)
                        # Use lightweight validation instead of expensive img.verify()
                        if self._is_valid_image_file(full_path):
                            self.photo_files.append(full_path)

            # Sort files by name for consistent ordering
            self.photo_files.sort(key=lambda x: os.path.basename(x).lower())

            if self.photo_files:
                self.current_photo_index = 0
                self.load_current_photo()
                self.update_status(f"Loaded {len(self.photo_files)} photos from {folder_path}")
            else:
                self.update_status("No valid JPEG files found in selected folder")
                QMessageBox.information(self, "No Photos", "No valid JPEG files found in the selected folder.")

        except Exception as e:
            self.update_status(f"Error loading folder: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load folder: {str(e)}")

    def _is_valid_image_file(self, file_path: str) -> bool:
        """Lightweight validation to check if file is a valid image."""
        try:
            # Check file size (skip very small files)
            if os.path.getsize(file_path) < 1024:  # Less than 1KB
                return False

            # Try to open with PIL (lightweight check)
            with Image.open(file_path) as img:
                # Just verify the format is supported
                return img.format in ['JPEG', 'JPG']
        except Exception:
            return False

    def _clear_image_caches(self):
        """Clear all image caches to free memory."""
        # Close all cached images
        for image in self.image_cache.values():
            try:
                image.close()
            except:
                pass

        self.image_cache.clear()
        self.scaled_cache.clear()

    def _manage_image_cache(self, cache, max_size):
        """Manage LRU cache size."""
        while len(cache) > max_size:
            # Remove oldest item (first item in OrderedDict)
            oldest_key, oldest_image = cache.popitem(last=False)
            try:
                oldest_image.close()
            except:
                pass

    def _get_cached_image(self, photo_path):
        """Get image from cache or load and cache it."""
        if photo_path in self.image_cache:
            # Move to end (most recently used)
            image = self.image_cache.pop(photo_path)
            self.image_cache[photo_path] = image
            return image

        # Load image and add to cache
        try:
            image = Image.open(photo_path)

            # Apply EXIF orientation correction
            image = self._apply_exif_orientation(image, photo_path)

            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

            # Add to cache
            self.image_cache[photo_path] = image
            self._manage_image_cache(self.image_cache, self.max_cache_size)

            return image
        except Exception as e:
            raise e

    def _apply_exif_orientation(self, image, photo_path):
        """Apply EXIF orientation correction to the image."""
        try:
            # Load EXIF data to check orientation
            exif_dict = piexif.load(photo_path)

            # Check for orientation tag in EXIF
            if "0th" in exif_dict and piexif.ImageIFD.Orientation in exif_dict["0th"]:
                orientation = exif_dict["0th"][piexif.ImageIFD.Orientation]

                # Apply rotation based on EXIF orientation
                if orientation == 2:
                    # Horizontal flip
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 3:
                    # 180 degree rotation
                    image = image.transpose(Image.ROT_180)
                elif orientation == 4:
                    # Vertical flip
                    image = image.transpose(Image.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    # Horizontal flip + 90 degree rotation
                    image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROT_90)
                elif orientation == 6:
                    # 90 degree rotation
                    image = image.transpose(Image.ROT_270)
                elif orientation == 7:
                    # Horizontal flip + 270 degree rotation
                    image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROT_270)
                elif orientation == 8:
                    # 270 degree rotation
                    image = image.transpose(Image.ROT_90)
                # orientation == 1 means no rotation needed (normal)

        except Exception as e:
            # If EXIF reading fails, just return the original image
            print(f"Warning: Could not read EXIF orientation for {photo_path}: {e}")

        return image

    def _get_cached_scaled_pixmap(self, photo_path, target_size):
        """Get scaled QPixmap from cache or create and cache it."""
        cache_key = f"{photo_path}_{target_size[0]}x{target_size[1]}"

        if cache_key in self.scaled_cache:
            # Move to end (most recently used)
            pixmap = self.scaled_cache.pop(cache_key)
            self.scaled_cache[cache_key] = pixmap
            return pixmap

        # Get original image (from cache or load)
        original_image = self._get_cached_image(photo_path)

        # Create scaled version
        resized_image = original_image.resize(target_size, Image.Resampling.LANCZOS)

        # Convert PIL image to QPixmap with proper handling
        try:
            qimage = self._pil_to_qpixmap(resized_image)
        except Exception as e:
            print(f"Error converting image to QPixmap: {e}")
            # Fallback: create a placeholder image
            qimage = QPixmap(target_size[0], target_size[1])
            qimage.fill(Qt.gray)

        # Add to cache
        self.scaled_cache[cache_key] = qimage
        self._manage_scaled_cache()

        return qimage

    def _pil_to_qpixmap(self, pil_image):
        """Convert PIL image to QPixmap with proper format handling."""
        # Ensure image is in RGB mode
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Get image data
        width, height = pil_image.size
        rgb_data = pil_image.tobytes('raw', 'RGB')

        # Calculate bytes per line (stride) - important for proper display
        bytes_per_line = width * 3  # 3 bytes per pixel for RGB

        # Create QImage with proper stride
        qimage = QImage(rgb_data, width, height, bytes_per_line, QImage.Format_RGB888)

        # Convert to QPixmap
        return QPixmap.fromImage(qimage)

    def _manage_scaled_cache(self):
        """Manage scaled image cache size."""
        while len(self.scaled_cache) > self.max_scaled_cache_size:
            # Remove oldest item
            self.scaled_cache.popitem(last=False)

    def load_current_photo(self):
        """Load and display the current photo using caching system."""
        if not self.photo_files:
            return

        photo_path = self.photo_files[self.current_photo_index]

        try:
            # Load image from cache
            self.current_image = self._get_cached_image(photo_path)

            # Scale image to fit viewer
            self.display_scaled_image()

            # Load metadata
            self.load_metadata()

            # Update navigation info
            filename = os.path.basename(photo_path)
            self.nav_info_label.setText(
                f"Photo {self.current_photo_index + 1} of {len(self.photo_files)} | {filename}"
            )

            # Update window title
            self.setWindowTitle(f"Photo Metadata Editor - {filename}")

            # Update copy button state
            self.update_copy_button_state()

            # Preload adjacent images in background
            self._preload_adjacent_images()

        except Exception as e:
            self.update_status(f"Error loading photo: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load photo {os.path.basename(photo_path)}: {str(e)}")

    def display_scaled_image(self):
        """Display the current image in the zoomable viewer."""
        if not self.current_image or not self.photo_files:
            return

        # Get the original image size
        img_width, img_height = self.current_image.size

        # Create a QPixmap from the original image (no pre-scaling needed)
        photo_path = self.photo_files[self.current_photo_index]

        # Use the original image size for the pixmap to maintain quality
        original_pixmap = self._get_cached_scaled_pixmap(photo_path, (img_width, img_height))

        # Set the image in the viewer (it will handle scaling automatically)
        self.photo_viewer.set_image(original_pixmap)

        # Hide placeholder and show viewer
        self.placeholder_label.hide()
        self.photo_viewer.show()

    def show_placeholder(self, message="Select a folder to view photos"):
        """Show placeholder message when no image is loaded."""
        self.placeholder_label.setText(message)
        self.placeholder_label.show()
        # Clear the image viewer
        if hasattr(self, 'photo_viewer'):
            self.photo_viewer.scene.clear()
            self.photo_viewer.has_image = False

    def _preload_adjacent_images(self):
        """Preload adjacent images in background for smooth navigation."""
        def preload_worker():
            try:
                # Preload next image
                if self.current_photo_index + 1 < len(self.photo_files):
                    next_path = self.photo_files[self.current_photo_index + 1]
                    self._get_cached_image(next_path)

                # Preload previous image
                if self.current_photo_index - 1 >= 0:
                    prev_path = self.photo_files[self.current_photo_index - 1]
                    self._get_cached_image(prev_path)
            except Exception as e:
                print(f"[DEBUG] Error preloading images: {e}")

        # Run preloading in background thread
        threading.Thread(target=preload_worker, daemon=True).start()

    def _debounced_navigation(self, direction):
        """Debounced navigation to prevent rapid key press issues."""
        import time
        current_time = time.time() * 1000  # Convert to milliseconds

        # If navigation is already pending, just update the direction and time
        if self._navigation_pending:
            self._last_navigation_time = current_time
            self._pending_direction = direction
            return

        # Start navigation
        self._navigation_pending = True
        self._last_navigation_time = current_time
        self._pending_direction = direction

        # Schedule the actual navigation
        self._navigation_timer.start(self._navigation_debounce_ms)

    def _execute_navigation(self):
        """Execute the pending navigation after debounce period."""
        import time
        current_time = time.time() * 1000

        # Check if enough time has passed since last navigation request
        if current_time - self._last_navigation_time < self._navigation_debounce_ms:
            # More navigation requests came in, wait a bit more
            self._navigation_timer.start(self._navigation_debounce_ms)
            return

        # Execute the navigation
        direction = self._pending_direction
        self._navigation_pending = False

        if direction == "previous":
            self._navigate_previous()
        elif direction == "next":
            self._navigate_next()

    def previous_photo(self):
        """Navigate to the previous photo with debouncing."""
        self._debounced_navigation("previous")

    def next_photo(self):
        """Navigate to the next photo with debouncing."""
        self._debounced_navigation("next")

    def _navigate_previous(self):
        """Internal method to navigate to previous photo."""
        if not self.photo_files:
            return

        if self.current_photo_index > 0:
            # Save any pending changes before navigating to prevent data loss
            self._save_pending_changes_before_navigation()

            # Store current photo metadata for "Copy from Previous" feature
            self.store_current_photo_metadata()

            self.current_photo_index -= 1
            self.load_current_photo()
        else:
            self.update_status("Already at first photo")

    def _navigate_next(self):
        """Internal method to navigate to next photo."""
        if not self.photo_files:
            return

        if self.current_photo_index < len(self.photo_files) - 1:
            # Save any pending changes before navigating to prevent data loss
            self._save_pending_changes_before_navigation()

            # Store current photo metadata for "Copy from Previous" feature
            self.store_current_photo_metadata()

            self.current_photo_index += 1
            self.load_current_photo()
        else:
            self.update_status("Already at last photo")

    def _save_pending_changes_before_navigation(self):
        """Save any pending metadata changes before navigating to prevent data loss."""
        if self.pending_changes:
            # Stop the auto-save timer to prevent race conditions
            self.auto_save_timer.stop()
            # Save immediately
            self.save_pending_metadata()

    def store_current_photo_metadata(self):
        """Store current photo metadata for copying to next photo."""
        if not self.photo_files:
            return

        current_metadata = {}

        # Store date
        date_text = self.date_entry.text().strip()
        if date_text:
            current_metadata['date'] = date_text

        # Store caption
        caption_text = self.caption_text.toPlainText().strip()
        if caption_text:
            current_metadata['caption'] = caption_text

        # Store location (only if it has coordinates)
        if self._last_selected_location:
            current_metadata['location'] = self._last_selected_location

        # Store the metadata
        self.previous_photo_metadata = current_metadata

    def update_copy_button_state(self):
        """Update the state of the Copy from Previous button."""
        if self.previous_photo_metadata and len(self.previous_photo_metadata) > 0:
            self.copy_from_previous_btn.setEnabled(True)
            # Update hint text to show what will be copied
            fields_to_copy = []
            if 'date' in self.previous_photo_metadata:
                fields_to_copy.append("date")
            if 'caption' in self.previous_photo_metadata:
                fields_to_copy.append("caption")
            if 'location' in self.previous_photo_metadata:
                fields_to_copy.append("location")

            if fields_to_copy:
                self.copy_hint_label.setText(f"Will copy: {', '.join(fields_to_copy)}")
            else:
                self.copy_hint_label.setText("No metadata to copy")
        else:
            self.copy_from_previous_btn.setEnabled(False)
            self.copy_hint_label.setText("No previous photo metadata available")

    def copy_from_previous_photo(self):
        """Copy metadata from the previous photo to the current photo."""
        if not self.previous_photo_metadata:
            return

        # Copy date
        if 'date' in self.previous_photo_metadata:
            self.date_entry.setText(self.previous_photo_metadata['date'])

        # Copy caption
        if 'caption' in self.previous_photo_metadata:
            self.caption_text.setPlainText(self.previous_photo_metadata['caption'])

        # Copy location
        if 'location' in self.previous_photo_metadata:
            location_data = self.previous_photo_metadata['location']
            self.location_entry.setText(location_data['address'])
            self._last_selected_location = location_data

        self.update_status("Metadata copied from previous photo")

    def load_metadata(self):
        """Load metadata from the current photo."""
        if not self.photo_files:
            return

        photo_path = self.photo_files[self.current_photo_index]

        try:
            # Mark metadata as not loaded during the loading process
            self._metadata_loaded = False

            # Temporarily disconnect signals to prevent triggering saves during field clearing
            self.date_entry.textChanged.disconnect()
            self.caption_text.textChanged.disconnect()
            self.location_entry.textChanged.disconnect()

            # Clear existing metadata fields
            self.date_entry.clear()
            self.caption_text.clear()
            self.location_entry.clear()

            # Clear last selected location data
            self._last_selected_location = None

            # Update photo info
            file_size = os.path.getsize(photo_path)
            file_size_mb = file_size / (1024 * 1024)
            img_width, img_height = self.current_image.size

            info_text = (f"File: {os.path.basename(photo_path)}\n"
                        f"Size: {img_width}×{img_height} pixels\n"
                        f"File size: {file_size_mb:.1f} MB")
            self.photo_info_label.setText(info_text)

            # Load EXIF data
            exif_dict = piexif.load(photo_path)

            # Load date from EXIF
            self.load_date_from_exif(exif_dict)

            # Load caption from EXIF
            self.load_caption_from_exif(exif_dict)

            # Load location from EXIF
            self.load_location_from_exif(exif_dict)

            # Mark metadata as successfully loaded
            self._metadata_loaded = True

        except Exception as e:
            self.update_status(f"Error loading metadata: {str(e)}")
            # Even on error, mark as loaded to prevent saving empty data
            self._metadata_loaded = True

        finally:
            # Always reconnect the signals after loading, regardless of success/failure
            self.date_entry.textChanged.connect(self.on_date_change)
            self.caption_text.textChanged.connect(self.on_caption_change)
            self.location_entry.textChanged.connect(self.on_location_change)

    def load_date_from_exif(self, exif_dict):
        """Load date from EXIF data."""
        try:
            # Try to get date from EXIF
            if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode('utf-8')
                # Convert EXIF date format to readable format
                date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                formatted_date = date_obj.strftime("%B %d, %Y")
                self.date_entry.setText(formatted_date)
            elif "0th" in exif_dict and piexif.ImageIFD.DateTime in exif_dict["0th"]:
                date_str = exif_dict["0th"][piexif.ImageIFD.DateTime].decode('utf-8')
                date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                formatted_date = date_obj.strftime("%B %d, %Y")
                self.date_entry.setText(formatted_date)
        except Exception as e:
            print(f"[DEBUG] Error loading date from EXIF: {e}")

    def load_caption_from_exif(self, exif_dict):
        """Load caption from EXIF data."""
        try:
            # Try to get caption from ImageDescription
            if "0th" in exif_dict and piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
                caption = exif_dict["0th"][piexif.ImageIFD.ImageDescription]
                if isinstance(caption, bytes):
                    caption = caption.decode('utf-8', errors='ignore')
                self.caption_text.setPlainText(caption)
        except Exception as e:
            print(f"[DEBUG] Error loading caption from EXIF: {e}")

    def load_location_from_exif(self, exif_dict):
        """Load location from EXIF GPS data."""
        try:
            if "GPS" in exif_dict:
                gps_data = exif_dict["GPS"]

                # Check if we have latitude and longitude
                if (piexif.GPSIFD.GPSLatitude in gps_data and
                    piexif.GPSIFD.GPSLongitude in gps_data):

                    # Extract coordinates
                    lat_data = gps_data[piexif.GPSIFD.GPSLatitude]
                    lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode('utf-8')
                    lon_data = gps_data[piexif.GPSIFD.GPSLongitude]
                    lon_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode('utf-8')

                    # Convert to decimal degrees
                    latitude = self.gps_to_decimal(lat_data, lat_ref)
                    longitude = self.gps_to_decimal(lon_data, lon_ref)

                    # Try to reverse geocode to get address
                    if self.geocoder:
                        try:
                            location = self.geocoder.reverse(f"{latitude}, {longitude}", timeout=5)
                            if location:
                                self.location_entry.setText(location.address)
                                self._last_selected_location = {
                                    'address': location.address,
                                    'latitude': latitude,
                                    'longitude': longitude
                                }
                        except Exception as e:
                            print(f"[DEBUG] Error reverse geocoding: {e}")
                            # Just show coordinates if reverse geocoding fails
                            self.location_entry.setText(f"{latitude:.6f}, {longitude:.6f}")

        except Exception as e:
            print(f"[DEBUG] Error loading location from EXIF: {e}")

    def gps_to_decimal(self, gps_data, ref):
        """Convert GPS coordinates to decimal degrees."""
        degrees = gps_data[0][0] / gps_data[0][1]
        minutes = gps_data[1][0] / gps_data[1][1]
        seconds = gps_data[2][0] / gps_data[2][1]

        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

        if ref in ['S', 'W']:
            decimal = -decimal

        return decimal

    def on_date_change(self):
        """Handle date field changes with real-time preview."""
        if not self.photo_files:
            return

        date_text = self.date_entry.text().strip()
        if not date_text:
            # Clear date from EXIF if empty
            self.schedule_metadata_save('date', None)
            self.hide_date_preview()
            return

        # Show real-time preview (but don't change the field content or auto-save)
        self.show_date_preview(date_text)

    def show_date_preview(self, date_text):
        """Show date preview dropdown."""
        # Parse date
        parsed_date = self.parse_natural_date(date_text)

        # Clear existing suggestions
        self.clear_date_suggestions()

        if not parsed_date:
            self.hide_date_preview()
            return

        # Show suggestions frame
        self.date_suggestions_frame.show()

        # Create preview button (styled to match location suggestions)
        preview_text = parsed_date.strftime('%B %d, %Y')
        suggestion_btn = QPushButton(f"📅 {preview_text}")
        suggestion_btn.clicked.connect(lambda: self.select_date_suggestion(parsed_date))
        # Apply consistent styling with location suggestions
        suggestion_btn.setMinimumHeight(30)
        self.date_suggestions_layout.addWidget(suggestion_btn)

    def hide_date_preview(self):
        """Hide date preview dropdown."""
        self.date_suggestions_frame.hide()
        self.clear_date_suggestions()

    def clear_date_suggestions(self):
        """Clear all date suggestion widgets."""
        while self.date_suggestions_layout.count():
            child = self.date_suggestions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def select_date_suggestion(self, parsed_date):
        """Select a date suggestion."""
        self.apply_date_confirmation(parsed_date)

    def eventFilter(self, obj, event):
        """Handle events for date input field."""
        if obj == self.date_entry:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    self.on_date_enter_key()
                    return True
                elif event.key() == Qt.Key_Tab:
                    self.on_date_tab_key()
                    # Let Tab continue to next widget
                    return False
            elif event.type() == QEvent.FocusOut:
                self.on_date_focus_out()
        return super().eventFilter(obj, event)

    def on_date_enter_key(self):
        """Handle Enter key press in date field."""
        date_text = self.date_entry.text().strip()
        if date_text:
            parsed_date = self.parse_natural_date(date_text)
            if parsed_date:
                self.apply_date_confirmation(parsed_date)
                # Move focus to next field (caption)
                self.caption_text.setFocus()

    def on_date_tab_key(self):
        """Handle Tab key press in date field."""
        date_text = self.date_entry.text().strip()
        if date_text:
            parsed_date = self.parse_natural_date(date_text)
            if parsed_date:
                self.apply_date_confirmation(parsed_date)

    def on_date_focus_out(self):
        """Handle date field losing focus."""
        date_text = self.date_entry.text().strip()
        if date_text:
            parsed_date = self.parse_natural_date(date_text)
            if parsed_date:
                self.apply_date_confirmation(parsed_date)
        # Small delay to allow click on preview button
        QTimer.singleShot(100, self.hide_date_preview)

    def apply_date_confirmation(self, parsed_date):
        """Apply confirmed date to field and save immediately."""
        if parsed_date:
            # Update entry field with formatted date
            formatted_date = parsed_date.strftime("%B %d, %Y")
            self.date_entry.setText(formatted_date)
            # Hide preview
            self.hide_date_preview()
            # Save the date immediately
            self.save_date_immediately(parsed_date)

    def parse_natural_date(self, date_text):
        """Parse natural language date input."""
        try:
            # Handle year-only input
            if date_text.isdigit() and len(date_text) == 4:
                year = int(date_text)
                if 1900 <= year <= 2100:
                    return datetime(year, 1, 1)

            # Use dateutil parser for flexible parsing
            parsed_date = date_parser.parse(date_text, fuzzy=True)

            # Validate reasonable date range
            if 1900 <= parsed_date.year <= 2100:
                return parsed_date
            else:
                return None
        except Exception:
            return None

    def save_date_immediately(self, parsed_date):
        """Save date immediately without auto-formatting during typing."""
        if not self.photo_files:
            return

        # Store the date change
        self.pending_changes['date'] = parsed_date

        # Save immediately without triggering the timer
        self.save_pending_metadata()

    def on_caption_change(self):
        """Handle caption field changes."""
        if not self.photo_files:
            return

        caption_text = self.caption_text.toPlainText().strip()

        # Schedule auto-save
        self.schedule_metadata_save('caption', caption_text if caption_text else None)
        self.update_status("Caption updated")

    def on_location_change(self):
        """Handle location field changes."""
        if not self.photo_files:
            return

        location_text = self.location_entry.text().strip()

        if not location_text:
            # Clear location from EXIF if empty
            self.schedule_metadata_save('location', None)
            self.hide_location_suggestions()
            return

        # Don't geocode very short text (less than 2 characters)
        if len(location_text) < 2:
            self.hide_location_suggestions()
            return

        # Schedule geocoding lookup
        if hasattr(self, '_geocoding_timer'):
            self._geocoding_timer.stop()
        self._geocoding_timer = QTimer()
        self._geocoding_timer.setSingleShot(True)
        self._geocoding_timer.timeout.connect(lambda: self.geocode_location(location_text))
        self._geocoding_timer.start(500)

    def schedule_metadata_save(self, field_type, value):
        """Schedule auto-save of metadata changes."""
        # Stop existing timer
        self.auto_save_timer.stop()

        # Store pending change
        self.pending_changes[field_type] = value

        # Schedule save after 1 second delay
        self.auto_save_timer.start(1000)

    def save_pending_metadata(self):
        """Save pending metadata changes to EXIF."""
        if not self.pending_changes or not self.photo_files:
            return

        # Don't save if metadata hasn't been properly loaded yet
        # This prevents saving empty data during rapid navigation
        if not self._metadata_loaded:
            return

        photo_path = self.photo_files[self.current_photo_index]

        try:
            # Create backup of original file
            backup_path = photo_path + ".backup"
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(photo_path, backup_path)

            # Load existing EXIF data
            try:
                exif_dict = piexif.load(photo_path)
            except Exception:
                # If no EXIF data exists, create empty structure
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

            # Apply pending changes
            for field_type, value in self.pending_changes.items():
                if field_type == 'date':
                    self.save_date_to_exif(exif_dict, value)
                elif field_type == 'caption':
                    self.save_caption_to_exif(exif_dict, value)
                elif field_type == 'location':
                    self.save_location_to_exif(exif_dict, value)

            # Write EXIF data back to file
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, photo_path)

            # Update auto-save status
            self.autosave_label.setText("✓ Changes saved automatically")
            self.autosave_label.setStyleSheet("QLabel { font-size: 10px; color: green; }")
            QTimer.singleShot(2000, lambda: self.autosave_label.setText("Changes are saved automatically"))
            QTimer.singleShot(2000, lambda: self.autosave_label.setStyleSheet("QLabel { font-size: 10px; color: gray; }"))

            self.update_status("Metadata saved")
            self.pending_changes.clear()

        except Exception as e:
            self.update_status(f"Error saving metadata: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save metadata: {str(e)}")

    def save_date_to_exif(self, exif_dict, date_value):
        """Save date to EXIF data."""
        if date_value is None:
            # Remove date fields
            if "Exif" in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
                del exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal]
            if "0th" in exif_dict and piexif.ImageIFD.DateTime in exif_dict["0th"]:
                del exif_dict["0th"][piexif.ImageIFD.DateTime]
        else:
            try:
                # Handle both string and datetime objects
                if isinstance(date_value, datetime):
                    parsed_date = date_value
                else:
                    # Parse the date string
                    parsed_date = date_parser.parse(date_value, fuzzy=True)
                exif_date_str = parsed_date.strftime("%Y:%m:%d %H:%M:%S")

                # Set in both DateTimeOriginal and DateTime
                if "Exif" not in exif_dict:
                    exif_dict["Exif"] = {}
                if "0th" not in exif_dict:
                    exif_dict["0th"] = {}

                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = exif_date_str.encode('utf-8')
                exif_dict["0th"][piexif.ImageIFD.DateTime] = exif_date_str.encode('utf-8')

            except Exception as e:
                print(f"[DEBUG] Error parsing date: {e}")

    def save_caption_to_exif(self, exif_dict, caption_text):
        """Save caption to EXIF data."""
        if caption_text is None:
            # Remove caption fields
            if "0th" in exif_dict and piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
                del exif_dict["0th"][piexif.ImageIFD.ImageDescription]
            if "Exif" in exif_dict and piexif.ExifIFD.UserComment in exif_dict["Exif"]:
                del exif_dict["Exif"][piexif.ExifIFD.UserComment]
        else:
            # Ensure we have the required dictionaries
            if "0th" not in exif_dict:
                exif_dict["0th"] = {}
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}

            caption_value = caption_text.strip()

            # Set caption in ImageDescription (primary field for Apple Photos)
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = caption_value.encode('utf-8')

            # Also set in UserComment for additional compatibility
            # UserComment needs special encoding
            user_comment = b"UNICODE\x00" + caption_value.encode('utf-8')
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment

    def save_location_to_exif(self, exif_dict, location_data):
        """Save location to EXIF GPS data with coordinates."""
        if location_data is None:
            # Remove GPS data completely
            if "GPS" in exif_dict:
                del exif_dict["GPS"]
        else:
            # Only save locations with valid coordinates (Apple Photos compatible)
            if ('latitude' in location_data and 'longitude' in location_data and
                location_data['latitude'] is not None and location_data['longitude'] is not None):
                # Save GPS coordinates
                # Ensure GPS dictionary exists
                if "GPS" not in exif_dict:
                    exif_dict["GPS"] = {}

                lat = location_data['latitude']
                lon = location_data['longitude']

                # Convert decimal degrees to GPS format
                lat_deg, lat_min, lat_sec = self.decimal_to_gps(abs(lat))
                lon_deg, lon_min, lon_sec = self.decimal_to_gps(abs(lon))

                # Set GPS data
                exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [(lat_deg, 1), (lat_min, 1), (int(lat_sec * 1000), 1000)]
                exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = 'N' if lat >= 0 else 'S'
                exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [(lon_deg, 1), (lon_min, 1), (int(lon_sec * 1000), 1000)]
                exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = 'E' if lon >= 0 else 'W'

    def decimal_to_gps(self, decimal_coord):
        """Convert decimal coordinate to GPS degrees, minutes, seconds."""
        degrees = int(decimal_coord)
        minutes_float = (decimal_coord - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        return degrees, minutes, seconds

    def geocode_location(self, location_text):
        """Geocode location text in background thread."""
        print(f"[DEBUG] geocode_location called with: '{location_text}'")

        # Show loading indicator
        self.show_location_loading()

        def geocode_worker():
            try:
                # Search for locations
                locations = self.geocoder.geocode(location_text, exactly_one=False, limit=5, timeout=5)

                if locations:
                    # Store locations for main thread processing
                    self._pending_locations = list(locations)
                    self._geocoding_results_ready = True
                else:
                    self._pending_locations = []
                    self._geocoding_results_ready = True

            except Exception as e:
                print(f"[DEBUG] Exception in geocode_worker: {type(e).__name__}: {str(e)}")
                # Handle different types of errors
                error_msg = str(e)
                if "timeout" in error_msg.lower():
                    error_msg = "Request timed out. Check your internet connection."
                elif isinstance(e, requests.exceptions.ConnectionError):
                    error_msg = "No internet connection available."
                elif "rate limit" in error_msg.lower():
                    error_msg = "Too many requests. Please wait a moment."
                else:
                    error_msg = f"Geocoding service error: {error_msg}"

                # Schedule error display in main thread
                QTimer.singleShot(0, lambda: self.show_location_error(error_msg))

        # Run geocoding in background thread
        threading.Thread(target=geocode_worker, daemon=True).start()

        # Start polling for results
        self._start_result_polling()

    def _start_result_polling(self):
        """Start polling for geocoding results."""
        if not hasattr(self, '_polling_timer'):
            self._polling_timer = QTimer()
            self._polling_timer.timeout.connect(self._check_geocoding_results)

        if not self._polling_timer.isActive():
            self._polling_timer.start(100)  # Check every 100ms

    def _check_geocoding_results(self):
        """Check if geocoding results are ready and process them."""
        if self._geocoding_results_ready:
            self._geocoding_results_ready = False
            self._polling_timer.stop()

            if self._pending_locations:
                locations = self._pending_locations
                self._pending_locations = None
                self.show_location_suggestions(locations)
            else:
                self.show_no_location_results()

    def show_location_suggestions(self, locations):
        """Show location suggestions dropdown."""
        # Clear existing suggestions
        self.clear_location_suggestions()

        # Store suggestions
        self.location_suggestions = locations[:5] if locations else []
        self.highlighted_suggestion_index = 0 if self.location_suggestions else -1

        if not locations:
            self.hide_location_suggestions()
            return

        # Show suggestions frame
        self.location_suggestions_frame.show()

        # Add suggestion buttons
        for i, location in enumerate(self.location_suggestions):
            suggestion_btn = QPushButton(location.address)
            suggestion_btn.clicked.connect(lambda checked, loc=location: self.select_location_suggestion(loc))
            self.location_suggestions_layout.addWidget(suggestion_btn)

    def clear_location_suggestions(self):
        """Clear all location suggestion widgets."""
        while self.location_suggestions_layout.count():
            child = self.location_suggestions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def hide_location_suggestions(self):
        """Hide location suggestions dropdown."""
        self.location_suggestions_frame.hide()
        self.clear_location_suggestions()
        self.location_suggestions = []
        self.highlighted_suggestion_index = -1

    def show_location_loading(self):
        """Show loading indicator for location geocoding."""
        self.clear_location_suggestions()
        self.location_suggestions_frame.show()

        loading_label = QLabel("🔍 Searching for locations...")
        loading_label.setStyleSheet("QLabel { font-size: 12px; }")
        self.location_suggestions_layout.addWidget(loading_label)

    def show_no_location_results(self):
        """Show message when no location results are found."""
        self.clear_location_suggestions()
        self.location_suggestions_frame.show()

        no_results_label = QLabel("❌ No locations found. Try a different search term.")
        no_results_label.setStyleSheet("QLabel { font-size: 12px; color: orange; }")
        self.location_suggestions_layout.addWidget(no_results_label)

        # Hide after 3 seconds
        QTimer.singleShot(3000, self.hide_location_suggestions)

    def show_location_error(self, error_message):
        """Show error message for location geocoding."""
        self.clear_location_suggestions()
        self.location_suggestions_frame.show()

        error_label = QLabel(f"⚠️ Error: {error_message}")
        error_label.setStyleSheet("QLabel { font-size: 12px; color: red; }")
        self.location_suggestions_layout.addWidget(error_label)

        # Hide after 5 seconds
        QTimer.singleShot(5000, self.hide_location_suggestions)
        self.update_status(f"Geocoding error: {error_message}")

    def select_location_suggestion(self, location):
        """Select a location suggestion."""
        # Update entry field
        self.location_entry.setText(location.address)

        # Hide suggestions
        self.hide_location_suggestions()

        # Save location with coordinates
        location_data = {
            'address': location.address,
            'latitude': location.latitude,
            'longitude': location.longitude
        }

        # Store for future copying
        self._last_selected_location = location_data

        self.schedule_metadata_save('location', location_data)
        self.update_status("Location updated")

    def hide_all_suggestions(self):
        """Hide all suggestion dropdowns."""
        self.hide_location_suggestions()
        self.hide_date_preview()

    def update_status(self, message: str):
        """Update the status bar."""
        self.status_bar.showMessage(message)

    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # The ZoomableImageViewer handles its own resize events
        # No need to manually trigger image redisplay

    def closeEvent(self, event):
        """Handle application close event."""
        self.cleanup()
        event.accept()

    def cleanup(self):
        """Clean up resources before closing."""
        # Stop any running timers
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()
        if hasattr(self, '_navigation_timer'):
            self._navigation_timer.stop()
        if hasattr(self, '_geocoding_timer'):
            self._geocoding_timer.stop()
        if hasattr(self, '_polling_timer'):
            self._polling_timer.stop()

        # Save any pending changes
        if self.pending_changes:
            self.save_pending_metadata()

        # Clean up image caches and free memory
        self._clear_image_caches()

        # Clean up current image references
        if hasattr(self, 'current_image') and self.current_image:
            try:
                self.current_image.close()
            except:
                pass

        # Clean up pixmap reference
        self.current_pixmap = None


def main():
    """Main entry point."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Photo Metadata Editor")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Photo Tools")

    # Create and show main window
    window = PhotoMetadataEditor()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
