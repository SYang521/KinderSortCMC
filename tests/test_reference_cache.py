"""Tests for the local reference encoding cache."""

import tempfile
import unittest
from pathlib import Path

from reference_cache import build_reference_manifest


class ReferenceManifestTests(unittest.TestCase):
    """Verify detection data for legacy and multi-photo references."""

    def test_manifest_includes_legacy_and_folder_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_folder = Path(temp_dir)

            legacy_photo = reference_folder / "Ali.jpg"
            legacy_photo.write_bytes(b"legacy-reference")

            student_folder = reference_folder / "Siti"
            student_folder.mkdir()
            folder_photo = student_folder / "front.jpg"
            folder_photo.write_bytes(b"folder-reference")

            manifest = build_reference_manifest(
                reference_folder,
                [
                    ("Ali", legacy_photo),
                    ("Siti", folder_photo),
                ],
            )

            self.assertEqual(
                [entry["relative_path"] for entry in manifest],
                ["Ali.jpg", "Siti/front.jpg"],
            )
            self.assertEqual(
                [entry["student_name"] for entry in manifest],
                ["Ali", "Siti"],
            )
            self.assertTrue(all(entry["size"] > 0 for entry in manifest))
            self.assertTrue(all(entry["modified_ns"] > 0 for entry in manifest))

    def test_manifest_changes_when_reference_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_folder = Path(temp_dir)
            reference_photo = reference_folder / "Ali.jpg"
            reference_photo.write_bytes(b"original")

            original_manifest = build_reference_manifest(
                reference_folder,
                [("Ali", reference_photo)],
            )

            reference_photo.write_bytes(b"modified-reference")

            modified_manifest = build_reference_manifest(
                reference_folder,
                [("Ali", reference_photo)],
            )

            self.assertNotEqual(original_manifest, modified_manifest)
    def test_manifest_rejects_image_outside_reference_folder(self) -> None:
        with tempfile.TemporaryDirectory() as reference_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                reference_folder = Path(reference_dir)
                outside_photo = Path(outside_dir) / "Outside.jpg"
                outside_photo.write_bytes(b"outside-reference")

                with self.assertRaisesRegex(
                    ValueError,
                    "outside the selected folder",
                ):
                    build_reference_manifest(
                        reference_folder,
                        [("Outside", outside_photo)],
                    )

if __name__ == "__main__":
    unittest.main()