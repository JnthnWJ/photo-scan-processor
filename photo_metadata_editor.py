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
        self._pending_locations = None
        self._geocoding_results_ready = False

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
        self.date_entry.bind("<Return>", self.on_date_enter_key)
        self.date_entry.bind("<FocusOut>", self.on_date_focus_out)
        self.date_entry.bind("<Tab>", self.on_date_tab_key)

        # Date preview dropdown frame
        self.date_preview_frame = ctk.CTkFrame(date_frame)
        self.date_preview_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.date_preview_frame.pack_forget()  # Initially hidden

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
        self.location_entry.bind("<Return>", self.on_location_enter_key)
        self.location_entry.bind("<FocusOut>", self.on_location_focus_out)
        self.location_entry.bind("<Tab>", self.on_location_tab_key)
        self.location_entry.bind("<Up>", self.on_location_up_key)
        self.location_entry.bind("<Down>", self.on_location_down_key)

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
        self.root.bind("<Escape>", lambda e: self.hide_all_suggestions())  # Esc to hide suggestions
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
        """Handle date field changes with real-time preview."""
        if not self.photo_files:
            return

        date_text = self.date_entry.get().strip()
        if not date_text:
            # Clear date from EXIF if empty
            self.schedule_metadata_save('date', None)
            self.hide_date_preview()
            return

        # Show real-time preview (but don't change the field content or auto-save)
        self.show_date_preview(date_text)

        # Don't auto-save or format until user explicitly accepts the date
        # This prevents interrupting the user's typing flow

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

    def parse_date_with_preview(self, date_text):
        """Parse date and return both parsed date and formatted preview text."""
        try:
            # Handle common formats
            original_text = date_text.strip()
            date_text = original_text.lower()

            # Handle year-only input
            if date_text.isdigit() and len(date_text) == 4:
                year = int(date_text)
                if 1900 <= year <= 2100:
                    parsed_date = datetime(year, 1, 1)
                    preview = parsed_date.strftime("%B %d, %Y")
                    return parsed_date, preview

            # Handle partial input with best guesses
            if date_text.isdigit():
                if len(date_text) == 1:
                    # Single digit - could be month or day
                    current_year = datetime.now().year
                    month = int(date_text)
                    if 1 <= month <= 12:
                        parsed_date = datetime(current_year, month, 1)
                        preview = f"{parsed_date.strftime('%B %d, %Y')} (assumed current year)"
                        return parsed_date, preview
                elif len(date_text) == 2:
                    # Two digits - could be year, month, or day
                    num = int(date_text)
                    current_year = datetime.now().year

                    # If it's a reasonable month (1-12), assume it's a month
                    if 1 <= num <= 12:
                        parsed_date = datetime(current_year, num, 1)
                        preview = f"{parsed_date.strftime('%B %d, %Y')} (assumed current year)"
                        return parsed_date, preview
                    # If it's a reasonable day (13-31), assume it's a day in current month
                    elif 13 <= num <= 31:
                        current_month = datetime.now().month
                        try:
                            parsed_date = datetime(current_year, current_month, num)
                            preview = f"{parsed_date.strftime('%B %d, %Y')} (assumed current month/year)"
                            return parsed_date, preview
                        except ValueError:
                            pass
                    # Otherwise, assume it's a year (19xx or 20xx)
                    else:
                        if num <= 30:
                            year = 2000 + num
                        else:
                            year = 1900 + num
                        if 1900 <= year <= 2100:
                            parsed_date = datetime(year, 1, 1)
                            preview = f"{parsed_date.strftime('%B %d, %Y')} (assumed year)"
                            return parsed_date, preview

            # Handle common partial formats
            if '/' in date_text or '-' in date_text:
                # Try to parse partial date formats
                parts = date_text.replace('-', '/').split('/')
                if len(parts) == 2:
                    # Month/day or month/year
                    try:
                        num1, num2 = int(parts[0]), int(parts[1])
                        current_year = datetime.now().year

                        # If second number is a 4-digit year
                        if 1900 <= num2 <= 2100:
                            parsed_date = datetime(num2, num1, 1)
                            preview = f"{parsed_date.strftime('%B %d, %Y')} (assumed 1st day)"
                            return parsed_date, preview
                        # If first number could be month and second could be day
                        elif 1 <= num1 <= 12 and 1 <= num2 <= 31:
                            try:
                                parsed_date = datetime(current_year, num1, num2)
                                preview = f"{parsed_date.strftime('%B %d, %Y')} (assumed current year)"
                                return parsed_date, preview
                            except ValueError:
                                pass
                    except ValueError:
                        pass

            # Use dateutil parser for flexible parsing
            parsed_date = date_parser.parse(original_text, fuzzy=True)

            # Validate reasonable date range
            if 1900 <= parsed_date.year <= 2100:
                preview = parsed_date.strftime("%B %d, %Y")
                return parsed_date, preview
            else:
                return None, "Date out of valid range (1900-2100)"

        except Exception:
            # Return a helpful message for invalid input
            return None, "Invalid date format"

    def show_date_preview(self, date_text):
        """Show date preview dropdown."""
        # Parse date and get preview
        parsed_date, preview_text = self.parse_date_with_preview(date_text)

        # Clear existing preview
        for widget in self.date_preview_frame.winfo_children():
            widget.destroy()

        if not preview_text or preview_text == "Invalid date format":
            self.hide_date_preview()
            return

        # Show preview frame
        self.date_preview_frame.pack(fill="x", padx=15, pady=(0, 10))

        # Create preview button
        preview_btn = ctk.CTkButton(
            self.date_preview_frame,
            text=f"📅 {preview_text}",
            height=30,
            command=lambda: self.select_date_preview(parsed_date, preview_text)
        )
        preview_btn.pack(fill="x", pady=2)

    def hide_date_preview(self, event=None):
        """Hide date preview dropdown."""
        self.date_preview_frame.pack_forget()

    def select_date_preview(self, parsed_date, preview_text):
        """Select the date preview and update the field."""
        if parsed_date:
            # Update entry field with formatted date
            formatted_date = parsed_date.strftime("%B %d, %Y")
            self.date_entry.delete(0, 'end')
            self.date_entry.insert(0, formatted_date)

            # Hide preview
            self.hide_date_preview()

            # Save the date immediately
            self.save_date_immediately(parsed_date)

    def on_date_enter_key(self, event=None):
        """Handle Enter key press in date field."""
        date_text = self.date_entry.get().strip()
        if date_text:
            parsed_date, preview_text = self.parse_date_with_preview(date_text)
            if parsed_date:
                self.select_date_preview(parsed_date, preview_text)
                # Move focus to next field (caption)
                self.caption_text.focus_set()
            else:
                # Still save what we can parse with the basic parser
                basic_parsed = self.parse_natural_date(date_text)
                if basic_parsed:
                    self.save_date_immediately(basic_parsed)
        return "break"  # Prevent default Enter behavior

    def on_date_focus_out(self, event=None):
        """Handle date field losing focus."""
        # Accept the current date if it's valid
        date_text = self.date_entry.get().strip()
        if date_text:
            parsed_date = self.parse_natural_date(date_text)
            if parsed_date:
                self.save_date_immediately(parsed_date)

        # Small delay to allow click on preview button
        self.root.after(100, self.hide_date_preview)

    def on_date_tab_key(self, event=None):
        """Handle Tab key press in date field."""
        # Accept current date if available
        date_text = self.date_entry.get().strip()
        if date_text:
            parsed_date, preview_text = self.parse_date_with_preview(date_text)
            if parsed_date:
                self.select_date_preview(parsed_date, preview_text)
            else:
                # Still save what we can parse with the basic parser
                basic_parsed = self.parse_natural_date(date_text)
                if basic_parsed:
                    self.save_date_immediately(basic_parsed)
        # Let default Tab behavior continue
        return None

    def hide_all_suggestions(self):
        """Hide all suggestion dropdowns."""
        self.hide_location_suggestions()
        self.hide_date_preview()

    def update_date_field_display(self):
        """Update the date field to show the final formatted date that will be saved."""
        if not self.photo_files:
            return

        # Only update if the field is not currently focused (user is not actively typing)
        if self.date_entry.focus_get() == self.date_entry:
            return

        # Get current date value from pending changes or parse current field
        current_date = None
        if 'date' in self.pending_changes:
            current_date = self.pending_changes['date']
        else:
            # Try to parse current field content
            date_text = self.date_entry.get().strip()
            if date_text:
                current_date = self.parse_natural_date(date_text)

        if current_date:
            # Format the date as it will appear in the final metadata
            formatted_date = current_date.strftime("%B %d, %Y")

            # Only update if different from current display
            current_display = self.date_entry.get().strip()
            if current_display != formatted_date:
                self.date_entry.delete(0, 'end')
                self.date_entry.insert(0, formatted_date)

    def schedule_metadata_save(self, field_type, value):
        """Schedule auto-save of metadata changes."""
        # Cancel existing timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)

        # Store pending change
        self.pending_changes[field_type] = value

        # Schedule save after 1 second delay
        self.auto_save_timer = self.root.after(1000, self.save_pending_metadata)

    def save_date_immediately(self, parsed_date):
        """Save date immediately without auto-formatting during typing."""
        if not self.photo_files:
            return

        # Store the date change
        self.pending_changes['date'] = parsed_date

        # Save immediately without triggering the timer
        self.save_pending_metadata()

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

            # Only update date field display if the date field is not currently focused
            # This prevents auto-formatting while the user is typing
            if self.date_entry.focus_get() != self.date_entry:
                self.update_date_field_display()

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

        # Update date field display to show final formatted date
        self.update_date_field_display()

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
        print(f"[DEBUG] on_location_change called")
        if not self.photo_files:
            print(f"[DEBUG] No photo files loaded, returning")
            return

        location_text = self.location_entry.get().strip()
        print(f"[DEBUG] Location text: '{location_text}'")

        if not location_text:
            # Clear location from EXIF if empty
            print(f"[DEBUG] Empty location text, clearing")
            self.schedule_metadata_save('location', None)
            self.hide_location_suggestions()
            return

        # Don't geocode very short text (less than 2 characters)
        if len(location_text) < 2:
            print(f"[DEBUG] Location text too short ({len(location_text)} chars), hiding suggestions")
            self.hide_location_suggestions()
            return

        # Schedule geocoding lookup
        print(f"[DEBUG] Scheduling geocoding for: '{location_text}'")
        if hasattr(self, '_geocoding_timer'):
            self.root.after_cancel(self._geocoding_timer)
        self._geocoding_timer = self.root.after(500, lambda: self.geocode_location(location_text))

        # Start polling for results if not already polling
        if not hasattr(self, '_polling_active') or not self._polling_active:
            self._start_result_polling()

    def geocode_location(self, location_text):
        """Geocode location text in background thread."""
        print(f"[DEBUG] geocode_location called with: '{location_text}'")

        # Show loading indicator
        print(f"[DEBUG] Showing loading indicator")
        self.show_location_loading()

        def geocode_worker():
            print(f"[DEBUG] geocode_worker thread started")
            try:
                print(f"[DEBUG] Calling geocoder.geocode with: '{location_text}'")
                print(f"[DEBUG] Geocoder object: {self.geocoder}")

                # Search for locations
                locations = self.geocoder.geocode(location_text, exactly_one=False, limit=5, timeout=5)
                print(f"[DEBUG] Geocoding completed. Results: {locations}")
                print(f"[DEBUG] Number of results: {len(locations) if locations else 0}")

                if locations:
                    print(f"[DEBUG] Setting geocoding results with {len(locations)} locations")
                    # Store locations and set flag for polling-based approach
                    self._pending_locations = list(locations)
                    self._geocoding_results_ready = True
                    print(f"[DEBUG] Results ready flag set to True")
                else:
                    print(f"[DEBUG] No results found, setting no results flag")
                    self._pending_locations = []
                    self._geocoding_results_ready = True

            except Exception as e:
                print(f"[DEBUG] Exception in geocode_worker: {type(e).__name__}: {str(e)}")
                import traceback
                print(f"[DEBUG] Full traceback: {traceback.format_exc()}")

                # Handle different types of errors
                import requests
                error_msg = str(e)
                if "timeout" in error_msg.lower():
                    error_msg = "Request timed out. Check your internet connection."
                elif isinstance(e, requests.exceptions.ConnectionError):
                    error_msg = "No internet connection available."
                elif "rate limit" in error_msg.lower():
                    error_msg = "Too many requests. Please wait a moment."
                else:
                    error_msg = f"Geocoding service error: {error_msg}"

                print(f"[DEBUG] Scheduling error message: {error_msg}")
                # Use functools.partial for error message too
                import functools
                error_callback = functools.partial(self.show_location_error, str(error_msg))
                self.root.after(0, error_callback)

            print(f"[DEBUG] geocode_worker thread ending")

        # Run geocoding in background thread
        print(f"[DEBUG] Starting geocoding thread")
        threading.Thread(target=geocode_worker, daemon=True).start()

    def _start_result_polling(self):
        """Start polling for geocoding results."""
        print(f"[DEBUG] Starting result polling")
        self._polling_active = True
        self._polling_timer = self.root.after(100, self._check_geocoding_results)

    def _check_geocoding_results(self):
        """Check if geocoding results are ready and process them."""
        if self._geocoding_results_ready:
            print(f"[DEBUG] Geocoding results ready! Processing...")
            self._geocoding_results_ready = False

            if self._pending_locations:
                print(f"[DEBUG] Processing {len(self._pending_locations)} locations")
                locations = self._pending_locations
                self._pending_locations = None
                self.show_location_suggestions(locations)
            else:
                print(f"[DEBUG] No locations found, showing no results")
                self.show_no_location_results()

        # Always continue polling (don't stop after processing results)
        self._polling_timer = self.root.after(100, self._check_geocoding_results)

    def _handle_geocoding_results(self):
        """Handle geocoding results in the main UI thread."""
        print(f"[DEBUG] _handle_geocoding_results called!")
        if hasattr(self, '_pending_locations') and self._pending_locations:
            print(f"[DEBUG] Processing {len(self._pending_locations)} pending locations")
            locations = self._pending_locations
            self._pending_locations = None  # Clear the pending locations
            self.show_location_suggestions(locations)
        else:
            print(f"[DEBUG] No pending locations found")

    def show_location_suggestions(self, locations):
        """Show location suggestions dropdown."""
        print(f"[DEBUG] show_location_suggestions called with {len(locations) if locations else 0} locations")

        # Store suggestions and reset highlighting
        self.location_suggestions = locations[:5] if locations else []
        self.highlighted_suggestion_index = 0 if self.location_suggestions else -1
        print(f"[DEBUG] Stored {len(self.location_suggestions)} suggestions")

        # Clear existing suggestions
        print(f"[DEBUG] Clearing existing suggestion widgets")
        for widget in self.location_suggestions_frame.winfo_children():
            widget.destroy()

        if not locations:
            print(f"[DEBUG] No locations provided, hiding suggestions")
            self.hide_location_suggestions()
            return

        # Show suggestions frame
        print(f"[DEBUG] Packing suggestions frame")
        self.location_suggestions_frame.pack(fill="x", padx=15, pady=(0, 10))

        # Add suggestion buttons
        print(f"[DEBUG] Creating suggestion buttons")
        for i, location in enumerate(self.location_suggestions):
            print(f"[DEBUG] Creating button {i}: {location.address}")
            suggestion_btn = ctk.CTkButton(
                self.location_suggestions_frame,
                text=location.address,
                height=30,
                command=lambda loc=location: self.select_location_suggestion(loc)
            )
            suggestion_btn.pack(fill="x", pady=2)

        # Apply initial highlighting
        print(f"[DEBUG] Applying initial highlighting")
        self.update_suggestion_highlighting()
        print(f"[DEBUG] show_location_suggestions completed")

    def hide_location_suggestions(self):
        """Hide location suggestions dropdown."""
        self.location_suggestions_frame.pack_forget()
        self.location_suggestions = []
        self.highlighted_suggestion_index = -1

    def update_suggestion_highlighting(self):
        """Update visual highlighting of location suggestions."""
        # Get all suggestion buttons
        suggestion_buttons = [widget for widget in self.location_suggestions_frame.winfo_children()
                            if isinstance(widget, ctk.CTkButton)]

        # Update button appearance based on highlighting
        for i, button in enumerate(suggestion_buttons):
            if i == self.highlighted_suggestion_index:
                # Highlight the selected suggestion
                button.configure(fg_color=("gray75", "gray25"))
            else:
                # Reset to default appearance
                button.configure(fg_color=("gray84", "gray25"))

    def show_location_loading(self):
        """Show loading indicator for location geocoding."""
        print(f"[DEBUG] show_location_loading called")

        # Clear existing suggestions
        print(f"[DEBUG] Clearing existing widgets for loading")
        for widget in self.location_suggestions_frame.winfo_children():
            widget.destroy()

        # Show suggestions frame with loading message
        print(f"[DEBUG] Packing loading frame")
        self.location_suggestions_frame.pack(fill="x", padx=15, pady=(0, 10))

        print(f"[DEBUG] Creating loading label")
        loading_label = ctk.CTkLabel(
            self.location_suggestions_frame,
            text="🔍 Searching for locations...",
            height=30,
            font=ctk.CTkFont(size=12)
        )
        loading_label.pack(fill="x", pady=2)
        print(f"[DEBUG] Loading indicator displayed")

    def show_no_location_results(self):
        """Show message when no location results are found."""
        # Clear existing suggestions
        for widget in self.location_suggestions_frame.winfo_children():
            widget.destroy()

        # Show suggestions frame with no results message
        self.location_suggestions_frame.pack(fill="x", padx=15, pady=(0, 10))

        no_results_label = ctk.CTkLabel(
            self.location_suggestions_frame,
            text="❌ No locations found. Try a different search term.",
            height=30,
            font=ctk.CTkFont(size=12),
            text_color="orange"
        )
        no_results_label.pack(fill="x", pady=2)

        # Hide after 3 seconds
        self.root.after(3000, self.hide_location_suggestions)

    def show_location_error(self, error_message):
        """Show error message for location geocoding."""
        # Clear existing suggestions
        for widget in self.location_suggestions_frame.winfo_children():
            widget.destroy()

        # Show suggestions frame with error message
        self.location_suggestions_frame.pack(fill="x", padx=15, pady=(0, 10))

        error_label = ctk.CTkLabel(
            self.location_suggestions_frame,
            text=f"⚠️ Error: {error_message}",
            height=30,
            font=ctk.CTkFont(size=12),
            text_color="red"
        )
        error_label.pack(fill="x", pady=2)

        # Hide after 5 seconds
        self.root.after(5000, self.hide_location_suggestions)
        self.update_status(f"Geocoding error: {error_message}")

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

        # Update date field display to show final formatted date
        self.update_date_field_display()

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

    def on_location_enter_key(self, event=None):
        """Handle Enter key press in location field."""
        if self.highlighted_suggestion_index >= 0 and self.location_suggestions:
            # Select the highlighted suggestion
            location = self.location_suggestions[self.highlighted_suggestion_index]
            self.select_location_suggestion(location)
            # Move focus to next field (caption)
            self.caption_text.focus_set()
        else:
            # If no suggestion is highlighted, try to geocode the current text
            location_text = self.location_entry.get().strip()
            if location_text:
                self.geocode_location(location_text)
        return "break"  # Prevent default Enter behavior

    def on_location_focus_out(self, event=None):
        """Handle location field losing focus."""
        # Small delay to allow click on suggestion button
        self.root.after(100, self.hide_location_suggestions)

    def on_location_tab_key(self, event=None):
        """Handle Tab key press in location field."""
        if self.highlighted_suggestion_index >= 0 and self.location_suggestions:
            # Select the highlighted suggestion
            location = self.location_suggestions[self.highlighted_suggestion_index]
            self.select_location_suggestion(location)
        # Let default Tab behavior continue
        return None

    def on_location_up_key(self, event=None):
        """Handle Up arrow key in location field."""
        if self.location_suggestions:
            if self.highlighted_suggestion_index > 0:
                self.highlighted_suggestion_index -= 1
            else:
                self.highlighted_suggestion_index = len(self.location_suggestions) - 1
            self.update_suggestion_highlighting()
        return "break"  # Prevent cursor movement

    def on_location_down_key(self, event=None):
        """Handle Down arrow key in location field."""
        if self.location_suggestions:
            if self.highlighted_suggestion_index < len(self.location_suggestions) - 1:
                self.highlighted_suggestion_index += 1
            else:
                self.highlighted_suggestion_index = 0
            self.update_suggestion_highlighting()
        return "break"  # Prevent cursor movement

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
