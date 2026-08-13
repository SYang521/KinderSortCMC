"""Integration tests for PhotoSorter reference encoding cache."""

import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from reference_cache import (
    build_cache_metadata,
    build_cache_paths,
    build_reference_manifest,
    save_reference_cache,
)
from sorter import PhotoSorter


class PhotoSorterCacheTests(unittest.TestCase):
    """Verify cache reuse in the reference loading pipeline."""

    def test_cache_hit_skips_reference_image_processing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            reference_folder = temp_root / "references"
            events_folder = temp_root / "events"
            output_folder = temp_root / "output"
            local_app_data = temp_root / "local-app-data"

            reference_folder.mkdir()
            events_folder.mkdir()
            output_folder.mkdir()
            local_app_data.mkdir()

            reference_photo = reference_folder / "Ali.jpg"
            reference_photo.write_bytes(b"synthetic-reference-file")

            logger = logging.getLogger(
                "kindersort-test-cache-hit"
            )
            sorter = PhotoSorter(
                reference_folder,
                events_folder,
                output_folder,
                logger,
            )

            reference_images = [
                ("Ali", reference_photo),
            ]
            reference_manifest = build_reference_manifest(
                reference_folder,
                reference_images,
            )
            encoding_config = sorter._reference_encoding_config()
            metadata = build_cache_metadata(
                reference_manifest,
                encoding_config,
            )
            cached_encodings = {
                "Ali": [
                    np.full(
                        sorter.ENCODING_DIMENSION,
                        0.25,
                        dtype=np.float64,
                    )
                ]
            }

            metadata_path, encodings_path = build_cache_paths(
                reference_folder,
                local_app_data,
            )
            save_reference_cache(
                metadata_path,
                encodings_path,
                metadata,
                cached_encodings,
            )

            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": str(local_app_data)},
            ):
                with patch(
                    "sorter.face_recognition.load_image_file"
                ) as load_image_file:
                    skipped_names = sorter.load_references()

            self.assertEqual(skipped_names, [])
            self.assertIn("Ali", sorter._student_encodings)
            self.assertEqual(
                len(sorter._student_encodings["Ali"]),
                1,
            )
            np.testing.assert_allclose(
                sorter._student_encodings["Ali"][0],
                cached_encodings["Ali"][0],
            )
            load_image_file.assert_not_called()


    def test_cache_miss_processes_reference_and_saves_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            reference_folder = temp_root / "references"
            events_folder = temp_root / "events"
            output_folder = temp_root / "output"
            local_app_data = temp_root / "local-app-data"

            reference_folder.mkdir()
            events_folder.mkdir()
            output_folder.mkdir()
            local_app_data.mkdir()

            reference_photo = reference_folder / "Ali.jpg"
            reference_photo.write_bytes(b"synthetic-reference-file")

            logger = logging.getLogger(
                "kindersort-test-cache-miss"
            )
            sorter = PhotoSorter(
                reference_folder,
                events_folder,
                output_folder,
                logger,
            )
            expected_encoding = np.full(
                sorter.ENCODING_DIMENSION,
                0.5,
                dtype=np.float64,
            )

            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": str(local_app_data)},
            ):
                with patch(
                    "sorter.face_recognition.load_image_file",
                    return_value=np.zeros(
                        (10, 10, 3),
                        dtype=np.uint8,
                    ),
                ) as load_image_file:
                    with patch(
                        "sorter.face_recognition.face_locations",
                        return_value=[(0, 9, 9, 0)],
                    ):
                        with patch(
                            "sorter.face_recognition.face_encodings",
                            return_value=[expected_encoding],
                        ):
                            skipped_names = sorter.load_references()

            metadata_path, encodings_path = build_cache_paths(
                reference_folder,
                local_app_data,
            )

            self.assertEqual(skipped_names, [])
            self.assertIn("Ali", sorter._student_encodings)
            load_image_file.assert_called_once_with(
                str(reference_photo)
            )
            self.assertTrue(metadata_path.is_file())
            self.assertTrue(encodings_path.is_file())


    def test_changed_reference_rebuilds_stale_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            reference_folder = temp_root / "references"
            events_folder = temp_root / "events"
            output_folder = temp_root / "output"
            local_app_data = temp_root / "local-app-data"

            reference_folder.mkdir()
            events_folder.mkdir()
            output_folder.mkdir()
            local_app_data.mkdir()

            reference_photo = reference_folder / "Ali.jpg"
            reference_photo.write_bytes(b"original-reference")

            logger = logging.getLogger(
                "kindersort-test-stale-cache"
            )
            sorter = PhotoSorter(
                reference_folder,
                events_folder,
                output_folder,
                logger,
            )

            original_manifest = build_reference_manifest(
                reference_folder,
                [("Ali", reference_photo)],
            )
            encoding_config = sorter._reference_encoding_config()
            original_metadata = build_cache_metadata(
                original_manifest,
                encoding_config,
            )
            stale_encoding = np.full(
                sorter.ENCODING_DIMENSION,
                0.1,
                dtype=np.float64,
            )

            metadata_path, encodings_path = build_cache_paths(
                reference_folder,
                local_app_data,
            )
            save_reference_cache(
                metadata_path,
                encodings_path,
                original_metadata,
                {"Ali": [stale_encoding]},
            )

            reference_photo.write_bytes(
                b"modified-reference-with-new-size"
            )
            rebuilt_encoding = np.full(
                sorter.ENCODING_DIMENSION,
                0.9,
                dtype=np.float64,
            )

            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": str(local_app_data)},
            ):
                with patch(
                    "sorter.face_recognition.load_image_file",
                    return_value=np.zeros(
                        (10, 10, 3),
                        dtype=np.uint8,
                    ),
                ) as load_image_file:
                    with patch(
                        "sorter.face_recognition.face_locations",
                        return_value=[(0, 9, 9, 0)],
                    ):
                        with patch(
                            "sorter.face_recognition.face_encodings",
                            return_value=[rebuilt_encoding],
                        ):
                            skipped_names = sorter.load_references()

            self.assertEqual(skipped_names, [])
            load_image_file.assert_called_once_with(
                str(reference_photo)
            )
            np.testing.assert_allclose(
                sorter._student_encodings["Ali"][0],
                rebuilt_encoding,
            )
            self.assertFalse(
                np.array_equal(
                    sorter._student_encodings["Ali"][0],
                    stale_encoding,
                )
            )


if __name__ == "__main__":
    unittest.main()