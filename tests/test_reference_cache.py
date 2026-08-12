"""Tests for the local reference encoding cache."""

import tempfile
import unittest
from pathlib import Path

from reference_cache import (
    CACHE_SCHEMA_VERSION,
    build_cache_metadata,
    build_cache_paths,
    build_reference_manifest,
    is_cache_metadata_valid,
)


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


class CachePathTests(unittest.TestCase):
    """Verify privacy-friendly per-folder cache paths."""

    def test_cache_path_uses_local_app_data_without_exposing_folder_name(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as local_app_data:
            reference_folder = Path(local_app_data) / "Private Class Names"
            reference_folder.mkdir()

            metadata_path, encodings_path = build_cache_paths(
                reference_folder,
                Path(local_app_data),
            )

            expected_root = (
                Path(local_app_data)
                / "KinderSortLite"
                / "cache"
            )

            self.assertEqual(metadata_path.parent, encodings_path.parent)
            self.assertEqual(metadata_path.parent.parent, expected_root)
            self.assertEqual(metadata_path.name, "metadata.json")
            self.assertEqual(encodings_path.name, "encodings.npz")
            self.assertNotIn(
                "Private Class Names",
                str(metadata_path),
            )

    def test_cache_path_is_stable_for_same_reference_folder(self) -> None:
        with tempfile.TemporaryDirectory() as local_app_data:
            reference_folder = Path(local_app_data) / "References"
            reference_folder.mkdir()

            first_paths = build_cache_paths(
                reference_folder,
                Path(local_app_data),
            )
            second_paths = build_cache_paths(
                reference_folder,
                Path(local_app_data),
            )

            self.assertEqual(first_paths, second_paths)

    def test_different_reference_folders_use_different_cache_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as local_app_data:
            first_folder = Path(local_app_data) / "Class A"
            second_folder = Path(local_app_data) / "Class B"
            first_folder.mkdir()
            second_folder.mkdir()

            first_paths = build_cache_paths(
                first_folder,
                Path(local_app_data),
            )
            second_paths = build_cache_paths(
                second_folder,
                Path(local_app_data),
            )

            self.assertNotEqual(
                first_paths[0].parent,
                second_paths[0].parent,
            )


class CacheMetadataTests(unittest.TestCase):
    """Verify cache version, manifest, and encoding configuration."""

    def setUp(self) -> None:
        self.manifest = [
            {
                "student_name": "Ali",
                "relative_path": "Ali/front.jpg",
                "size": 1234,
                "modified_ns": 5678,
            }
        ]
        self.encoding_config = {
            "face_location_model": "cnn",
            "num_jitters": 10,
            "encoding_model": "large",
            "encoding_dimension": 128,
        }

    def test_metadata_is_valid_for_matching_inputs(self) -> None:
        metadata = build_cache_metadata(
            self.manifest,
            self.encoding_config,
        )

        self.assertEqual(
            metadata["schema_version"],
            CACHE_SCHEMA_VERSION,
        )
        self.assertTrue(
            is_cache_metadata_valid(
                metadata,
                self.manifest,
                self.encoding_config,
            )
        )

    def test_metadata_is_invalid_after_reference_change(self) -> None:
        metadata = build_cache_metadata(
            self.manifest,
            self.encoding_config,
        )
        changed_manifest = [
            {
                **self.manifest[0],
                "size": 9999,
            }
        ]

        self.assertFalse(
            is_cache_metadata_valid(
                metadata,
                changed_manifest,
                self.encoding_config,
            )
        )

    def test_metadata_is_invalid_for_different_encoding_config(self) -> None:
        metadata = build_cache_metadata(
            self.manifest,
            self.encoding_config,
        )
        changed_config = {
            **self.encoding_config,
            "num_jitters": 5,
        }

        self.assertFalse(
            is_cache_metadata_valid(
                metadata,
                self.manifest,
                changed_config,
            )
        )

    def test_metadata_is_invalid_for_unsupported_schema_version(self) -> None:
        metadata = build_cache_metadata(
            self.manifest,
            self.encoding_config,
        )
        metadata["schema_version"] = CACHE_SCHEMA_VERSION + 1

        self.assertFalse(
            is_cache_metadata_valid(
                metadata,
                self.manifest,
                self.encoding_config,
            )
        )

    def test_malformed_metadata_is_invalid(self) -> None:
        malformed_values = [
            None,
            "invalid metadata",
            [],
            {},
            {"schema_version": CACHE_SCHEMA_VERSION},
        ]

        for metadata in malformed_values:
            with self.subTest(metadata=metadata):
                self.assertFalse(
                    is_cache_metadata_valid(
                        metadata,
                        self.manifest,
                        self.encoding_config,
                    )
                )


if __name__ == "__main__":
    unittest.main()
