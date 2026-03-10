#!/usr/bin/env python3
"""
Focused tests for non-destructive photo editing and crop workflow.
"""

import os
import tempfile
import shutil
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import piexif
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from photo_metadata_editor_qt import (
        PhotoMetadataEditor,
        PhotoEditState,
        DateStampState,
        apply_photo_adjustments,
        apply_date_stamp_overlay,
        clamp_normalized_rect,
        normalized_rect_to_pixel_box,
    )
    DEPS_AVAILABLE = True
except ModuleNotFoundError:
    DEPS_AVAILABLE = False


@unittest.skipUnless(DEPS_AVAILABLE, "PySide6 + piexif + app dependencies are required")
class TestImageEditing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="photo_editing_test_")
        self.photo1 = os.path.join(self.temp_dir, "photo_1.jpg")
        self.photo2 = os.path.join(self.temp_dir, "photo_2.jpg")
        self._create_photo(self.photo1, color=(190, 120, 80))
        self._create_photo(self.photo2, color=(80, 150, 200))

        self.window = PhotoMetadataEditor()
        self.window.load_folder(self.temp_dir)

    def tearDown(self):
        self.window.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_photo(self, path, color=(160, 140, 120)):
        img = Image.new("RGB", (480, 320), color=color)
        for x in range(0, 480, 10):
            for y in range(0, 320, 10):
                img.putpixel((x, y), ((x * 3) % 255, (y * 5) % 255, ((x + y) * 2) % 255))

        exif_dict = {
            "0th": {
                piexif.ImageIFD.ImageDescription: b"Test caption",
                piexif.ImageIFD.DateTime: b"2024:01:01 12:00:00",
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2024:01:01 12:00:00",
            },
            "GPS": {},
            "1st": {},
            "thumbnail": None,
        }
        img.save(path, quality=95, exif=piexif.dump(exif_dict))

    def _clear_photo_date(self, path):
        exif_dict = piexif.load(path)
        exif_dict.setdefault("Exif", {}).pop(piexif.ExifIFD.DateTimeOriginal, None)
        exif_dict.setdefault("0th", {}).pop(piexif.ImageIFD.DateTime, None)
        piexif.insert(piexif.dump(exif_dict), path)

    def test_draft_edits_do_not_modify_file_until_save(self):
        before_bytes = open(self.photo1, "rb").read()
        state = self.window.get_or_create_edit_state(self.photo1)
        state.brightness = 35
        self.window._set_state_dirty(state)
        self.window.render_edit_preview()
        after_bytes = open(self.photo1, "rb").read()
        self.assertEqual(before_bytes, after_bytes)

    def test_save_edits_overwrites_original_and_creates_single_backup(self):
        before_bytes = open(self.photo1, "rb").read()
        state = self.window.get_or_create_edit_state(self.photo1)
        state.saturation = 30
        state.crop_rect_norm = (0.1, 0.1, 0.9, 0.9)
        self.window._set_state_dirty(state)

        result = self.window.save_current_image_edits()
        self.assertTrue(result)
        after_bytes = open(self.photo1, "rb").read()
        self.assertNotEqual(before_bytes, after_bytes)

        backup_path = self.photo1 + ".backup"
        self.assertTrue(os.path.exists(backup_path))
        self.assertEqual(open(backup_path, "rb").read(), before_bytes)

        state = self.window.get_or_create_edit_state(self.photo1)
        state.brightness = 20
        self.window._set_state_dirty(state)
        self.assertTrue(self.window.save_current_image_edits())
        self.assertEqual(len([p for p in os.listdir(self.temp_dir) if p.endswith(".backup")]), 1)

    def test_exif_is_preserved_after_image_save(self):
        state = self.window.get_or_create_edit_state(self.photo1)
        state.contrast = 25
        self.window._set_state_dirty(state)
        self.assertTrue(self.window.save_current_image_edits())

        exif_dict = piexif.load(self.photo1)
        self.assertIn(piexif.ExifIFD.DateTimeOriginal, exif_dict["Exif"])
        self.assertIn(piexif.ImageIFD.ImageDescription, exif_dict["0th"])
        self.assertEqual(exif_dict["0th"][piexif.ImageIFD.ImageDescription], b"Test caption")

    def test_crop_normalization_and_remap(self):
        clamped = clamp_normalized_rect((-0.5, 0.2, 1.3, 0.1))
        self.assertGreater(clamped[2], clamped[0])
        self.assertGreater(clamped[3], clamped[1])

        rect_norm = (0.1, 0.2, 0.7, 0.8)
        self.assertEqual(normalized_rect_to_pixel_box(rect_norm, 1000, 500), (100, 100, 700, 400))
        self.assertEqual(normalized_rect_to_pixel_box(rect_norm, 2000, 1000), (200, 200, 1400, 800))

        test_image = Image.new("RGB", (100, 100), color=(128, 128, 128))
        edit_state = PhotoEditState(crop_rect_norm=(0.25, 0.25, 0.75, 0.75))
        cropped = apply_photo_adjustments(test_image, edit_state, apply_crop=True)
        self.assertEqual(cropped.size, (50, 50))

    def test_navigation_prompt_save_discard_cancel(self):
        # Cancel
        state = self.window.get_or_create_edit_state(self.photo1)
        state.brightness = 20
        self.window._set_state_dirty(state)
        self.window.prompt_unsaved_image_edits = lambda: "cancel"
        self.window._navigate_next()
        self.assertEqual(self.window.current_photo_index, 0)

        # Discard
        state = self.window.get_or_create_edit_state(self.photo1)
        state.brightness = 20
        self.window._set_state_dirty(state)
        calls = {"discard": 0}

        def fake_discard():
            calls["discard"] += 1
            self.window.photo_edit_states[self.photo1] = PhotoEditState()
            return True

        self.window.prompt_unsaved_image_edits = lambda: "discard"
        self.window.discard_current_image_edits = fake_discard
        self.window._navigate_next()
        self.assertEqual(calls["discard"], 1)
        self.assertEqual(self.window.current_photo_index, 1)

        # Save
        self.window._navigate_previous()
        state = self.window.get_or_create_edit_state(self.photo1)
        state.brightness = 30
        self.window._set_state_dirty(state)
        calls = {"save": 0}

        def fake_save():
            calls["save"] += 1
            self.window.photo_edit_states[self.photo1] = PhotoEditState()
            return True

        self.window.prompt_unsaved_image_edits = lambda: "save"
        self.window.save_current_image_edits = fake_save
        self.window._navigate_next()
        self.assertEqual(calls["save"], 1)
        self.assertEqual(self.window.current_photo_index, 1)

    def test_realtime_adjustment_pipeline_changes_pixels(self):
        base = Image.new("RGB", (32, 32))
        for x in range(32):
            for y in range(32):
                base.putpixel((x, y), ((x * 7) % 255, (y * 11) % 255, ((x + y) * 5) % 255))

        for field_name, value in [
            ("brightness", 25),
            ("contrast", 25),
            ("saturation", 25),
            ("temperature", 30),
            ("tint", 30),
        ]:
            state = PhotoEditState()
            setattr(state, field_name, value)
            adjusted = apply_photo_adjustments(base, state, apply_crop=False)
            self.assertNotEqual(base.tobytes(), adjusted.tobytes(), msg=f"{field_name} did not change output")

    def test_stamp_draft_does_not_modify_file_until_save(self):
        before_bytes = open(self.photo1, "rb").read()
        self.window.stamp_enabled_checkbox.setChecked(True)
        self.assertEqual(self.window.stamp_text_entry.text(), "January 01, 2024")
        after_bytes = open(self.photo1, "rb").read()
        self.assertEqual(before_bytes, after_bytes)

    def test_stamp_save_changes_pixels_without_double_applying(self):
        self.window.stamp_enabled_checkbox.setChecked(True)
        self.window.on_stamp_text_edited("JAN 01 2024")

        before_bytes = open(self.photo1, "rb").read()
        self.assertTrue(self.window.save_current_image_edits())
        first_saved_bytes = open(self.photo1, "rb").read()
        self.assertNotEqual(before_bytes, first_saved_bytes)

        self.assertTrue(self.window.save_current_image_edits())
        second_saved_bytes = open(self.photo1, "rb").read()
        self.assertEqual(first_saved_bytes, second_saved_bytes)

    def test_stamp_autofill_sync_and_manual_override(self):
        self.window.stamp_enabled_checkbox.setChecked(True)
        state = self.window.get_or_create_edit_state(self.photo1).date_stamp
        self.assertEqual(state.text, "January 01, 2024")
        self.assertEqual(state.text_mode, "auto_date")

        self.window.date_entry.setText("February 02, 1999")
        state = self.window.get_or_create_edit_state(self.photo1).date_stamp
        self.assertEqual(state.text, "February 02, 1999")
        self.assertEqual(state.text_mode, "auto_date")

        self.window.on_stamp_text_edited("Custom note")
        self.window.date_entry.setText("March 03, 2003")
        state = self.window.get_or_create_edit_state(self.photo1).date_stamp
        self.assertEqual(state.text, "Custom note")
        self.assertEqual(state.text_mode, "manual")

    def test_stamp_defaults_carry_forward_but_remain_disabled(self):
        self.window.stamp_enabled_checkbox.setChecked(True)
        self.window.stamp_color_combo.setCurrentIndex(self.window.stamp_color_combo.findData("white"))
        self.window.stamp_font_combo.setCurrentIndex(self.window.stamp_font_combo.findData("courier_prime"))
        self.window.adjust_stamp_font_size(2)
        self.window.on_stamp_rect_moved((0.88, 0.82, 0.98, 0.92))
        self.assertTrue(self.window.save_current_image_edits())

        self.window._navigate_next()
        next_state = self.window.get_or_create_edit_state(self.photo2).date_stamp
        self.assertFalse(next_state.enabled)
        self.assertEqual(next_state.text, "")

        self.window.stamp_enabled_checkbox.setChecked(True)
        next_state = self.window.get_or_create_edit_state(self.photo2).date_stamp
        self.assertTrue(next_state.enabled)
        self.assertEqual(next_state.color, "white")
        self.assertEqual(next_state.font_key, "courier_prime")
        self.assertEqual(next_state.size_adjust, 2)
        self.assertEqual(next_state.anchor_corner, "custom")
        self.assertAlmostEqual(next_state.position_norm[0], 0.88, places=2)
        self.assertAlmostEqual(next_state.position_norm[1], 0.82, places=2)

    def test_navigation_does_not_apply_stale_date_focus_out_to_next_photo(self):
        self._clear_photo_date(self.photo2)
        self.window.date_entry.setText("February 02, 1999")

        original_load_current_photo = self.window.load_current_photo
        stale_focus_out_triggered = {"value": False}

        def load_with_stale_focus_out():
            if self.window.current_photo_index == 1 and not stale_focus_out_triggered["value"]:
                stale_focus_out_triggered["value"] = True
                self.window.on_date_focus_out()
            return original_load_current_photo()

        self.window.load_current_photo = load_with_stale_focus_out
        self.window._navigate_next()

        self.assertTrue(stale_focus_out_triggered["value"])
        exif_dict = piexif.load(self.photo2)
        self.assertNotIn(piexif.ExifIFD.DateTimeOriginal, exif_dict["Exif"])
        self.assertNotIn(piexif.ImageIFD.DateTime, exif_dict["0th"])
        self.assertEqual(self.window.current_photo_index, 1)
        self.assertEqual(self.window.date_entry.text().strip(), "")

    def test_stamp_size_controls_and_open_sans_option(self):
        self.window.stamp_enabled_checkbox.setChecked(True)

        font_keys = [
            self.window.stamp_font_combo.itemData(i)
            for i in range(self.window.stamp_font_combo.count())
        ]
        self.assertIn("open_sans", font_keys)

        state = self.window.get_or_create_edit_state(self.photo1).date_stamp
        self.assertEqual(state.size_adjust, 0)
        self.window.adjust_stamp_font_size(1)
        self.assertEqual(state.size_adjust, 1)
        self.assertEqual(self.window.stamp_size_label.text(), "+1")
        self.window.adjust_stamp_font_size(-1)
        self.assertEqual(state.size_adjust, 0)
        self.assertEqual(self.window.stamp_size_label.text(), "Default")

    def test_stamp_corner_and_drag_positions_are_bounded(self):
        self.window.stamp_enabled_checkbox.setChecked(True)
        self.window.stamp_corner_combo.setCurrentIndex(self.window.stamp_corner_combo.findData("top_right"))
        state = self.window.get_or_create_edit_state(self.photo1).date_stamp
        self.assertEqual(state.anchor_corner, "top_right")
        self.assertIsNone(state.position_norm)

        self.window.on_stamp_rect_moved((-0.4, 1.5, 0.2, 1.8))
        state = self.window.get_or_create_edit_state(self.photo1).date_stamp
        self.assertEqual(state.anchor_corner, "custom")
        self.assertGreaterEqual(state.position_norm[0], 0.0)
        self.assertLessEqual(state.position_norm[0], 1.0)
        self.assertGreaterEqual(state.position_norm[1], 0.0)
        self.assertLessEqual(state.position_norm[1], 1.0)

    def test_orange_stamp_glow_differs_from_flat_colors(self):
        base = Image.new("RGB", (300, 200), color=(20, 20, 20))
        orange_state = DateStampState(enabled=True, text="13  9  9", color="orange")
        white_state = DateStampState(enabled=True, text="13  9  9", color="white")
        black_state = DateStampState(enabled=True, text="13  9  9", color="black")

        orange_image, _ = apply_date_stamp_overlay(base, orange_state, self.window._stamp_font_for_pil)
        white_image, _ = apply_date_stamp_overlay(base, white_state, self.window._stamp_font_for_pil)
        black_image, _ = apply_date_stamp_overlay(base, black_state, self.window._stamp_font_for_pil)

        self.assertNotEqual(orange_image.tobytes(), white_image.tobytes())
        self.assertNotEqual(orange_image.tobytes(), black_image.tobytes())


if __name__ == "__main__":
    unittest.main()
