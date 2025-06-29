#!/usr/bin/env python3
"""
Photo Metadata Editor
A desktop application for editing metadata of scanned photos with Apple Photos compatibility.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import piexif
from datetime import datetime
from dateutil import parser as date_parser
from geopy.geocoders import Nominatim
import threading
import time
from typing import List, Optional, Dict, Any


class PhotoMetadataEditor:
    """Main application class for the Photo Metadata Editor."""
    
    def __init__(self):
        """Initialize the application."""
        # Set appearance mode and color theme
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("Photo Metadata Editor")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Application state
        self.current_folder = None
        self.photo_files = []
        self.current_photo_index = 0
        self.current_image = None
        self.current_photo_ctk = None
        
        # Geocoder for location suggestions
        self.geocoder = Nominatim(user_agent="photo_metadata_editor")
        
        # Auto-save timer
        self.auto_save_timer = None
        self.pending_changes = {}
        
        # Setup UI
        self.setup_ui()
        self.setup_keyboard_bindings()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=2)  # Photo viewer
        self.root.grid_columnconfigure(1, weight=1)  # Metadata panel
        self.root.grid_rowconfigure(1, weight=1)     # Main content area
        
        # Top toolbar
        self.create_toolbar()
        
        # Main content area
        self.create_photo_viewer()
        self.create_metadata_panel()
        
        # Status bar
        self.create_status_bar()
        
    def create_toolbar(self):
        """Create the top toolbar."""
        toolbar_frame = ctk.CTkFrame(self.root)
        toolbar_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        # Select folder button
        self.select_folder_btn = ctk.CTkButton(
            toolbar_frame,
            text="Select Folder",
            command=self.select_folder,
            width=120
        )
        self.select_folder_btn.pack(side="left", padx=10, pady=10)

        # Help button
        self.help_btn = ctk.CTkButton(
            toolbar_frame,
            text="Help",
            command=self.show_help,
            width=80
        )
        self.help_btn.pack(side="left", padx=5, pady=10)

        # Folder path label
        self.folder_path_label = ctk.CTkLabel(
            toolbar_frame,
            text="No folder selected - Press Ctrl+O or click 'Select Folder'",
            font=ctk.CTkFont(size=12)
        )
        self.folder_path_label.pack(side="left", padx=20, pady=10)
        
    def create_photo_viewer(self):
        """Create the photo viewer area."""
        self.photo_frame = ctk.CTkFrame(self.root)
        self.photo_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        self.photo_frame.grid_columnconfigure(0, weight=1)
        self.photo_frame.grid_rowconfigure(0, weight=1)
        
        # Photo display label
        self.photo_label = ctk.CTkLabel(
            self.photo_frame,
            text="Select a folder to view photos",
            font=ctk.CTkFont(size=16)
        )
        self.photo_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Navigation info
        self.nav_info_label = ctk.CTkLabel(
            self.photo_frame,
            text="Use ← → arrow keys to navigate",
            font=ctk.CTkFont(size=12)
        )
        self.nav_info_label.grid(row=1, column=0, pady=10)
        
    def create_metadata_panel(self):
        """Create the metadata editing panel."""
        self.metadata_frame = ctk.CTkFrame(self.root)
        self.metadata_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)

        # Create scrollable frame for metadata fields
        self.metadata_scroll = ctk.CTkScrollableFrame(self.metadata_frame)
        self.metadata_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            self.metadata_scroll,
            text="Photo Metadata",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 20))

        # Current photo info
        self.photo_info_frame = ctk.CTkFrame(self.metadata_scroll)
        self.photo_info_frame.pack(fill="x", pady=(0, 20))

        self.photo_info_label = ctk.CTkLabel(
            self.photo_info_frame,
            text="No photo selected",
            font=ctk.CTkFont(size=12),
            wraplength=250
        )
        self.photo_info_label.pack(padx=10, pady=10)

        # Date field
        self.create_date_field()

        # Caption field
        self.create_caption_field()

        # Location field
        self.create_location_field()

        # Auto-save status
        self.autosave_label = ctk.CTkLabel(
            self.metadata_scroll,
            text="Changes are saved automatically",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.autosave_label.pack(pady=(20, 10))
        
    def create_date_field(self):
        """Create the date input field."""
        date_frame = ctk.CTkFrame(self.metadata_scroll)
        date_frame.pack(fill="x", pady=10)

        date_label = ctk.CTkLabel(date_frame, text="Date:", font=ctk.CTkFont(weight="bold"))
        date_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.date_entry = ctk.CTkEntry(
            date_frame,
            placeholder_text="e.g., 2001, 5/11/01, jan 1 2001",
            height=35
        )
        self.date_entry.pack(fill="x", padx=15, pady=(0, 10))
        self.date_entry.bind("<KeyRelease>", self.on_date_change)
        self.date_entry.bind("<Button-1>", lambda e: self.date_entry.focus_set())

        # Date format hint
        date_hint = ctk.CTkLabel(
            date_frame,
            text="Accepts natural language dates",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        date_hint.pack(anchor="w", padx=15, pady=(0, 15))
        
    def create_caption_field(self):
        """Create the caption/description field."""
        caption_frame = ctk.CTkFrame(self.metadata_scroll)
        caption_frame.pack(fill="x", pady=10)

        caption_label = ctk.CTkLabel(caption_frame, text="Caption/Description:", font=ctk.CTkFont(weight="bold"))
        caption_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.caption_text = ctk.CTkTextbox(caption_frame, height=100)
        self.caption_text.pack(fill="x", padx=15, pady=(0, 10))
        self.caption_text.bind("<KeyRelease>", self.on_caption_change)
        self.caption_text.bind("<Button-1>", lambda e: self.caption_text.focus_set())

        # Caption hint
        caption_hint = ctk.CTkLabel(
            caption_frame,
            text="Description will be visible in Apple Photos",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        caption_hint.pack(anchor="w", padx=15, pady=(0, 15))
        
    def create_location_field(self):
        """Create the location input field with geocoding."""
        location_frame = ctk.CTkFrame(self.metadata_scroll)
        location_frame.pack(fill="x", pady=10)

        location_label = ctk.CTkLabel(location_frame, text="Location:", font=ctk.CTkFont(weight="bold"))
        location_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.location_entry = ctk.CTkEntry(
            location_frame,
            placeholder_text="e.g., Boulder, Colorado",
            height=35
        )
        self.location_entry.pack(fill="x", padx=15, pady=(0, 10))
        self.location_entry.bind("<KeyRelease>", self.on_location_change)
        self.location_entry.bind("<Button-1>", lambda e: self.location_entry.focus_set())

        # Location suggestions frame
        self.location_suggestions_frame = ctk.CTkFrame(location_frame)
        self.location_suggestions_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.location_suggestions_frame.pack_forget()  # Initially hidden

        # Location hint
        location_hint = ctk.CTkLabel(
            location_frame,
            text="GPS coordinates will be added to photo metadata",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        location_hint.pack(anchor="w", padx=15, pady=(0, 15))
        
    def create_status_bar(self):
        """Create the status bar."""
        self.status_frame = ctk.CTkFrame(self.root)
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
    def setup_keyboard_bindings(self):
        """Set up keyboard bindings for navigation."""
        self.root.bind("<Left>", self.previous_photo)
        self.root.bind("<Right>", self.next_photo)
        self.root.bind("<Configure>", self.handle_window_resize)
        self.root.bind("<Control-o>", lambda e: self.select_folder())  # Ctrl+O to open folder
        self.root.bind("<Escape>", lambda e: self.hide_location_suggestions())  # Esc to hide suggestions
        self.root.focus_set()  # Ensure window can receive key events

        # Make sure the window can receive focus for keyboard events, but only when clicking on non-input areas
        self.root.bind("<Button-1>", self.handle_root_click)

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def handle_root_click(self, event):
        """Handle clicks on the root window, but allow input fields to receive focus."""
        # Get the widget that was clicked
        clicked_widget = event.widget

        # Check if the clicked widget is an input field or its parent
        widget_class_name = clicked_widget.__class__.__name__

        # Don't steal focus from input widgets
        if widget_class_name in ['CTkEntry', 'CTkTextbox']:
            return

        # Check if we clicked on a child of an input widget
        parent = clicked_widget
        while parent:
            if hasattr(parent, '__class__'):
                parent_class_name = parent.__class__.__name__
                if parent_class_name in ['CTkEntry', 'CTkTextbox']:
                    return
            parent = getattr(parent, 'master', None)

        # If we get here, it's safe to set focus to root for keyboard navigation
        self.root.focus_set()

    def on_closing(self):
        """Handle window closing event."""
        self.cleanup()
        self.root.destroy()

    def show_help(self):
        """Show help dialog."""
        help_text = """Photo Metadata Editor - Help

NAVIGATION:
• Use ← → arrow keys to navigate between photos
• Click 'Select Folder' or press Ctrl+O to choose a photo folder

METADATA EDITING:
• Date: Enter dates in natural language (e.g., "2001", "5/11/01", "jan 1 2001")
• Caption: Add descriptions that will appear in Apple Photos
• Location: Type location names for GPS coordinates and suggestions

FEATURES:
• All changes are saved automatically to EXIF data
• Metadata is compatible with Apple Photos
• GPS coordinates are added for location entries
• Supports JPEG files with EXIF data

KEYBOARD SHORTCUTS:
• Ctrl+O: Open folder
• ← →: Navigate photos
• Esc: Hide location suggestions

The application creates backup files (.backup) before modifying originals."""

        messagebox.showinfo("Help - Photo Metadata Editor", help_text)
        
    def select_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(title="Select folder containing photos")
        if folder:
            self.load_folder(folder)
            
    def load_folder(self, folder_path: str):
        """Load photos from the selected folder."""
        try:
            self.current_folder = folder_path
            self.folder_path_label.configure(text=f"Folder: {os.path.basename(folder_path)}")

            # Find JPEG files recursively
            self.photo_files = []
            supported_extensions = ('.jpg', '.jpeg', '.JPG', '.JPEG')

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(supported_extensions):
                        full_path = os.path.join(root, file)
                        # Verify it's actually a valid image file
                        try:
                            with Image.open(full_path) as img:
                                img.verify()  # Verify it's a valid image
                            self.photo_files.append(full_path)
                        except Exception:
                            # Skip invalid image files
                            continue

            # Sort files by name for consistent ordering
            self.photo_files.sort(key=lambda x: os.path.basename(x).lower())

            if self.photo_files:
                self.current_photo_index = 0
                self.load_current_photo()
                self.update_status(f"Loaded {len(self.photo_files)} photos from {folder_path}")

                # Enable keyboard focus for navigation
                self.root.focus_set()
            else:
                self.update_status("No valid JPEG files found in selected folder")
                messagebox.showinfo("No Photos", "No valid JPEG files found in the selected folder.")

        except Exception as e:
            self.update_status(f"Error loading folder: {str(e)}")
            messagebox.showerror("Error", f"Failed to load folder: {str(e)}")
            
    def load_current_photo(self):
        """Load and display the current photo."""
        if not self.photo_files:
            return

        photo_path = self.photo_files[self.current_photo_index]

        try:
            # Load image
            self.current_image = Image.open(photo_path)

            # Convert to RGB if necessary (for JPEG compatibility)
            if self.current_image.mode not in ('RGB', 'L'):
                self.current_image = self.current_image.convert('RGB')

            # Scale image to fit viewer
            self.display_scaled_image()

            # Load metadata
            self.load_metadata()

            # Update navigation info
            filename = os.path.basename(photo_path)
            self.nav_info_label.configure(
                text=f"Photo {self.current_photo_index + 1} of {len(self.photo_files)} | {filename}"
            )

            # Update window title
            self.root.title(f"Photo Metadata Editor - {filename}")

        except Exception as e:
            self.update_status(f"Error loading photo: {str(e)}")
            messagebox.showerror("Error", f"Failed to load photo {os.path.basename(photo_path)}: {str(e)}")
            
    def display_scaled_image(self):
        """Scale and display the current image."""
        if not self.current_image:
            return

        # Get viewer dimensions
        viewer_width = self.photo_frame.winfo_width()
        viewer_height = self.photo_frame.winfo_height()

        if viewer_width <= 1 or viewer_height <= 1:
            # Window not yet properly sized, try again later
            self.root.after(100, self.display_scaled_image)
            return

        # Calculate scaling to fit within viewer
        img_width, img_height = self.current_image.size
        scale_x = (viewer_width - 40) / img_width
        scale_y = (viewer_height - 80) / img_height  # Leave space for navigation info
        scale = min(scale_x, scale_y, 1.0)  # Don't scale up

        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        # Resize image
        resized_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create CTkImage for better compatibility
        self.current_photo_ctk = ctk.CTkImage(
            light_image=resized_image,
            dark_image=resized_image,
            size=(new_width, new_height)
        )

        # Update label
        self.photo_label.configure(image=self.current_photo_ctk, text="")

    def handle_window_resize(self, event=None):
        """Handle window resize events to rescale the image."""
        if self.current_image and event and event.widget == self.root:
            # Delay the rescaling to avoid too many rapid updates
            if hasattr(self, '_resize_timer'):
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(100, self.display_scaled_image)
        
    def load_metadata(self):
        """Load metadata from the current photo."""
        if not self.photo_files:
            return

        photo_path = self.photo_files[self.current_photo_index]

        try:
            # Clear existing metadata fields
            self.date_entry.delete(0, 'end')
            self.caption_text.delete("1.0", 'end')
            self.location_entry.delete(0, 'end')

            # Update photo info
            file_size = os.path.getsize(photo_path)
            file_size_mb = file_size / (1024 * 1024)
            img_width, img_height = self.current_image.size

            info_text = (f"File: {os.path.basename(photo_path)}\n"
                        f"Size: {img_width}×{img_height} pixels\n"
                        f"File size: {file_size_mb:.1f} MB")
            self.photo_info_label.configure(text=info_text)

            # Load EXIF data
            exif_dict = piexif.load(photo_path)

            # Load date from EXIF
            self.load_date_from_exif(exif_dict)

            # Load caption from EXIF
            self.load_caption_from_exif(exif_dict)

            # Load location from EXIF
            self.load_location_from_exif(exif_dict)

        except Exception as e:
            self.update_status(f"Error loading metadata: {str(e)}")

    def load_date_from_exif(self, exif_dict):
        """Load date from EXIF data."""
        try:
            # Try different EXIF date fields
            date_fields = [
                exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal),
                exif_dict.get("0th", {}).get(piexif.ImageIFD.DateTime)
            ]

            for date_field in date_fields:
                if date_field:
                    # EXIF date format: "YYYY:MM:DD HH:MM:SS"
                    date_str = date_field.decode('utf-8') if isinstance(date_field, bytes) else date_field
                    try:
                        parsed_date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        formatted_date = parsed_date.strftime("%B %d, %Y")
                        self.date_entry.insert(0, formatted_date)
                        break
                    except ValueError:
                        continue

        except Exception as e:
            pass  # No date found or error parsing

    def load_caption_from_exif(self, exif_dict):
        """Load caption from EXIF data."""
        try:
            # Try different caption/description fields
            caption_fields = [
                exif_dict.get("0th", {}).get(piexif.ImageIFD.ImageDescription),
                exif_dict.get("Exif", {}).get(piexif.ExifIFD.UserComment)
            ]

            for caption_field in caption_fields:
                if caption_field:
                    caption_str = caption_field.decode('utf-8') if isinstance(caption_field, bytes) else caption_field
                    # Remove null characters and clean up
                    caption_str = caption_str.replace('\x00', '').strip()
                    if caption_str:
                        self.caption_text.insert("1.0", caption_str)
                        break

        except Exception as e:
            pass  # No caption found or error parsing

    def load_location_from_exif(self, exif_dict):
        """Load location from EXIF GPS data."""
        try:
            gps_info = exif_dict.get("GPS", {})
            if not gps_info:
                return

            # Extract GPS coordinates
            lat = self.convert_gps_coordinate(
                gps_info.get(piexif.GPSIFD.GPSLatitude),
                gps_info.get(piexif.GPSIFD.GPSLatitudeRef)
            )
            lon = self.convert_gps_coordinate(
                gps_info.get(piexif.GPSIFD.GPSLongitude),
                gps_info.get(piexif.GPSIFD.GPSLongitudeRef)
            )

            if lat is not None and lon is not None:
                # Try to reverse geocode to get location name
                try:
                    location = self.geocoder.reverse(f"{lat}, {lon}", timeout=5)
                    if location:
                        self.location_entry.insert(0, location.address)
                except Exception:
                    # If reverse geocoding fails, just show coordinates
                    self.location_entry.insert(0, f"{lat:.6f}, {lon:.6f}")

        except Exception as e:
            pass  # No GPS data found or error parsing

    def convert_gps_coordinate(self, coord_tuple, ref):
        """Convert GPS coordinate from EXIF format to decimal degrees."""
        if not coord_tuple or not ref:
            return None

        try:
            degrees = coord_tuple[0][0] / coord_tuple[0][1]
            minutes = coord_tuple[1][0] / coord_tuple[1][1]
            seconds = coord_tuple[2][0] / coord_tuple[2][1]

            decimal = degrees + minutes/60 + seconds/3600

            ref_str = ref.decode('utf-8') if isinstance(ref, bytes) else ref
            if ref_str in ['S', 'W']:
                decimal = -decimal

            return decimal
        except Exception:
            return None
        
    def previous_photo(self, event=None):
        """Navigate to the previous photo."""
        if self.photo_files and self.current_photo_index > 0:
            self.current_photo_index -= 1
            self.load_current_photo()
            self.update_status(f"Photo {self.current_photo_index + 1} of {len(self.photo_files)}")
        elif self.photo_files:
            self.update_status("Already at first photo")

    def next_photo(self, event=None):
        """Navigate to the next photo."""
        if self.photo_files and self.current_photo_index < len(self.photo_files) - 1:
            self.current_photo_index += 1
            self.load_current_photo()
            self.update_status(f"Photo {self.current_photo_index + 1} of {len(self.photo_files)}")
        elif self.photo_files:
            self.update_status("Already at last photo")
            
    def on_date_change(self, event=None):
        """Handle date field changes."""
        if not self.photo_files:
            return

        date_text = self.date_entry.get().strip()
        if not date_text:
            # Clear date from EXIF if empty
            self.schedule_metadata_save('date', None)
            return

        try:
            # Parse natural language date
            parsed_date = self.parse_natural_date(date_text)
            if parsed_date:
                # Schedule auto-save
                self.schedule_metadata_save('date', parsed_date)
                self.update_status("Date updated")
            else:
                self.update_status("Invalid date format")

        except Exception as e:
            self.update_status(f"Date parsing error: {str(e)}")

    def parse_natural_date(self, date_text):
        """Parse natural language date input."""
        try:
            # Handle common formats
            date_text = date_text.strip().lower()

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

    def schedule_metadata_save(self, field_type, value):
        """Schedule auto-save of metadata changes."""
        # Cancel existing timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)

        # Store pending change
        self.pending_changes[field_type] = value

        # Schedule save after 1 second delay
        self.auto_save_timer = self.root.after(1000, self.save_pending_metadata)

    def save_pending_metadata(self):
        """Save pending metadata changes to EXIF."""
        if not self.photo_files or not self.pending_changes:
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
            self.autosave_label.configure(text="✓ Changes saved automatically", text_color="green")
            self.root.after(2000, lambda: self.autosave_label.configure(
                text="Changes are saved automatically", text_color="gray"))

            self.update_status("Metadata saved")
            self.pending_changes.clear()

        except Exception as e:
            self.update_status(f"Error saving metadata: {str(e)}")
            self.autosave_label.configure(text="⚠ Error saving changes", text_color="red")
            self.root.after(3000, lambda: self.autosave_label.configure(
                text="Changes are saved automatically", text_color="gray"))

    def save_date_to_exif(self, exif_dict, date_value):
        """Save date to EXIF data."""
        if date_value is None:
            # Remove date fields
            if "Exif" in exif_dict:
                exif_dict["Exif"].pop(piexif.ExifIFD.DateTimeOriginal, None)
            if "0th" in exif_dict:
                exif_dict["0th"].pop(piexif.ImageIFD.DateTime, None)
        else:
            # Format date for EXIF: "YYYY:MM:DD HH:MM:SS"
            date_str = date_value.strftime("%Y:%m:%d %H:%M:%S")

            # Ensure EXIF and 0th dictionaries exist
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}
            if "0th" not in exif_dict:
                exif_dict["0th"] = {}

            # Set date in multiple fields for compatibility
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
            exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
        
    def on_caption_change(self, event=None):
        """Handle caption field changes."""
        if not self.photo_files:
            return

        caption_text = self.caption_text.get("1.0", 'end-1c').strip()

        # Schedule auto-save
        self.schedule_metadata_save('caption', caption_text if caption_text else None)
        self.update_status("Caption updated")

    def save_caption_to_exif(self, exif_dict, caption_value):
        """Save caption to EXIF data."""
        if caption_value is None or not caption_value.strip():
            # Remove caption fields
            if "0th" in exif_dict:
                exif_dict["0th"].pop(piexif.ImageIFD.ImageDescription, None)
            if "Exif" in exif_dict:
                exif_dict["Exif"].pop(piexif.ExifIFD.UserComment, None)
        else:
            # Ensure 0th and Exif dictionaries exist
            if "0th" not in exif_dict:
                exif_dict["0th"] = {}
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}

            # Set caption in ImageDescription (primary field for Apple Photos)
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = caption_value

            # Also set in UserComment for additional compatibility
            # UserComment needs special encoding
            user_comment = b"UNICODE\x00" + caption_value.encode('utf-8')
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment
        
    def on_location_change(self, event=None):
        """Handle location field changes."""
        if not self.photo_files:
            return

        location_text = self.location_entry.get().strip()

        if not location_text:
            # Clear location from EXIF if empty
            self.schedule_metadata_save('location', None)
            self.hide_location_suggestions()
            return

        # Schedule geocoding lookup
        if hasattr(self, '_geocoding_timer'):
            self.root.after_cancel(self._geocoding_timer)
        self._geocoding_timer = self.root.after(500, lambda: self.geocode_location(location_text))

    def geocode_location(self, location_text):
        """Geocode location text in background thread."""
        def geocode_worker():
            try:
                # Search for locations
                locations = self.geocoder.geocode(location_text, exactly_one=False, limit=5, timeout=5)
                if locations:
                    # Update UI in main thread
                    self.root.after(0, lambda: self.show_location_suggestions(locations))
                else:
                    self.root.after(0, self.hide_location_suggestions)
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Geocoding error: {str(e)}"))

        # Run geocoding in background thread
        threading.Thread(target=geocode_worker, daemon=True).start()

    def show_location_suggestions(self, locations):
        """Show location suggestions dropdown."""
        # Clear existing suggestions
        for widget in self.location_suggestions_frame.winfo_children():
            widget.destroy()

        if not locations:
            self.hide_location_suggestions()
            return

        # Show suggestions frame
        self.location_suggestions_frame.pack(fill="x", padx=15, pady=(0, 10))

        # Add suggestion buttons
        for i, location in enumerate(locations[:5]):  # Limit to 5 suggestions
            suggestion_btn = ctk.CTkButton(
                self.location_suggestions_frame,
                text=location.address,
                height=30,
                command=lambda loc=location: self.select_location_suggestion(loc)
            )
            suggestion_btn.pack(fill="x", pady=2)

    def hide_location_suggestions(self):
        """Hide location suggestions dropdown."""
        self.location_suggestions_frame.pack_forget()

    def select_location_suggestion(self, location):
        """Select a location suggestion."""
        # Update entry field
        self.location_entry.delete(0, 'end')
        self.location_entry.insert(0, location.address)

        # Hide suggestions
        self.hide_location_suggestions()

        # Save location with coordinates
        location_data = {
            'address': location.address,
            'latitude': location.latitude,
            'longitude': location.longitude
        }
        self.schedule_metadata_save('location', location_data)
        self.update_status("Location updated")

    def save_location_to_exif(self, exif_dict, location_data):
        """Save location to EXIF GPS data."""
        if location_data is None:
            # Remove GPS data
            if "GPS" in exif_dict:
                del exif_dict["GPS"]
        else:
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
        
    def update_status(self, message: str):
        """Update the status bar."""
        self.status_label.configure(text=message)
        
    def run(self):
        """Start the application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.cleanup()
        except Exception as e:
            messagebox.showerror("Application Error", f"An unexpected error occurred: {str(e)}")
            self.cleanup()

    def cleanup(self):
        """Clean up resources before closing."""
        # Cancel any pending timers
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        if hasattr(self, '_geocoding_timer'):
            self.root.after_cancel(self._geocoding_timer)
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)

        # Save any pending changes
        if self.pending_changes:
            self.save_pending_metadata()


def main():
    """Main entry point."""
    app = PhotoMetadataEditor()
    app.run()


if __name__ == "__main__":
    main()
