"""
sorter.py — Face recognition logic for KinderSort.

PhotoSorter loads reference encodings and sorts event photos into per-student
output folders.  All processing is CPU-only (no GPU required).
"""

import logging
import os
from collections.abc import Callable
from pathlib import Path

import face_recognition
import numpy as np
from PIL import Image, UnidentifiedImageError

from reference_cache import (
    build_cache_metadata,
    build_cache_paths,
    build_reference_manifest,
    load_reference_cache,
    save_reference_cache,
)

from utils import (
    build_output_filename,
    collect_event_images,
    is_image_file,
    safe_copy,
)


class PhotoSorter:
    """Encapsulates the full sort pipeline from reference loading to file copying.

    Usage::

        sorter = PhotoSorter(reference_folder, events_folder, output_folder, logger)
        skipped_names = sorter.load_references()   # sync, may show warnings
        summary = sorter.sort_all(progress_cb, cancelled_cb)
    """

    DISTANCE_THRESHOLD = 0.55
    """Maximum face distance to consider a match (lower = stricter)."""

    MAX_IMAGE_DIMENSION = 1000
    """Longest side in pixels after resizing for face detection (performance)."""
    REFERENCE_FACE_LOCATION_MODEL = "cnn"
    REFERENCE_NUM_JITTERS = 10
    REFERENCE_ENCODING_MODEL = "large"
    ENCODING_DIMENSION = 128

    def _reference_encoding_config(self) -> dict[str, object]:
        """Return parameters that determine reference encoding contents."""
        return {
            "face_location_model": self.REFERENCE_FACE_LOCATION_MODEL,
            "num_jitters": self.REFERENCE_NUM_JITTERS,
            "encoding_model": self.REFERENCE_ENCODING_MODEL,
            "encoding_dimension": self.ENCODING_DIMENSION,
        }

    def _cache_paths(self) -> tuple[Path, Path] | None:
        """Return local cache paths, or None if LOCALAPPDATA is unavailable."""
        local_app_data = os.environ.get("LOCALAPPDATA")

        if not local_app_data:
            self.logger.warning(
                "LOCALAPPDATA is unavailable; reference cache is disabled."
            )
            return None

        return build_cache_paths(
            self.reference_folder,
            Path(local_app_data),
        )

    def __init__(
        self,
        reference_folder: Path,
        events_folder: Path,
        output_folder: Path,
        logger: logging.Logger,
    ) -> None:
        """Store folder paths and logger; initialise empty encoding dict."""
        self.reference_folder = reference_folder
        self.events_folder = events_folder
        self.output_folder = output_folder
        self.logger = logger
        self._student_encodings: dict[str, list[np.ndarray]] = {}

    # ------------------------------------------------------------------
    # Reference loading
    # ------------------------------------------------------------------

    def _collect_reference_images(self) -> list[tuple[str, Path]]:
        """Collect reference images from legacy files and student folders."""
        reference_images: list[tuple[str, Path]] = []

        for item in sorted(self.reference_folder.iterdir()):
            if item.is_file() and is_image_file(item):
                reference_images.append((item.stem, item))
                continue

            if item.is_dir():
                for image_path in sorted(item.iterdir()):
                    if image_path.is_file() and is_image_file(image_path):
                        reference_images.append((item.name, image_path))

        return reference_images

    def load_references(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[str]:
        """Encode every reference photo and store by student name.

        Iterates over image files in reference_folder.  The student name is the
        filename stem (e.g. ``Ali.jpg`` → ``"Ali"``).

        Args:
            progress_callback: Optional callable with ``(current, total, name)``
                called after each student is processed so the GUI can update.

        Returns:
            List of student names whose reference photo had no detectable face.
            Callers should show a warning for each name in this list.
        """
        no_face_names: list[str] = []
        reference_images = self._collect_reference_images()

        reference_manifest = build_reference_manifest(
            self.reference_folder,
            reference_images,
        )
        encoding_config = self._reference_encoding_config()
        cache_paths = self._cache_paths()

        if cache_paths is not None:
            metadata_path, encodings_path = cache_paths
            cached_encodings = load_reference_cache(
                metadata_path,
                encodings_path,
                reference_manifest,
                encoding_config,
            )

            if cached_encodings is not None:
                self._student_encodings = cached_encodings
                self.logger.info(
                    "Loaded %d student reference(s) from local cache",
                    len(self._student_encodings),
                )
                return no_face_names

        if not reference_images:
            self.logger.warning("No reference images found in %s", self.reference_folder)
            return no_face_names

        total = len(reference_images)
        for current, (student_name, ref_path) in enumerate(
            reference_images, start=1
        ):
            if progress_callback:
                progress_callback(current, total, student_name)
            try:
                image = face_recognition.load_image_file(str(ref_path))
                locations = face_recognition.face_locations(
                    image,
                    model=self.REFERENCE_FACE_LOCATION_MODEL,
                )
                encodings = face_recognition.face_encodings(
                    image,
                    known_face_locations=locations,
                    num_jitters=self.REFERENCE_NUM_JITTERS,
                    model=self.REFERENCE_ENCODING_MODEL,
                )

                if not encodings:
                    self.logger.warning(
                        "No face detected in reference photo for %s (%s)",
                        student_name,
                        ref_path.relative_to(self.reference_folder),
                    )
                    no_face_names.append(student_name)
                    continue

                if len(encodings) > 1:
                    self.logger.warning(
                        "Multiple faces in reference photo for %s (%s) – using first face only",
                        student_name,
                        ref_path.relative_to(self.reference_folder),
                    )

                self._student_encodings.setdefault(student_name, []).append(encodings[0])
                self.logger.info(
                    "Loaded reference for %s from %s",
                    student_name,
                    ref_path.relative_to(self.reference_folder),
                )

            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Could not read reference photo for %s (%s): %s",
                    student_name,
                    ref_path.relative_to(self.reference_folder),
                    exc,
                )

        self.logger.info(
            "Loaded %d student reference(s)", len(self._student_encodings)
        )

        if cache_paths is not None and self._student_encodings:
            metadata_path, encodings_path = cache_paths
            cache_metadata = build_cache_metadata(
                reference_manifest,
                encoding_config,
            )

            try:
                save_reference_cache(
                    metadata_path,
                    encodings_path,
                    cache_metadata,
                    self._student_encodings,
                )
                self.logger.info(
                    "Saved reference encodings to local cache."
                )
            except (OSError, TypeError, ValueError) as exc:
                self.logger.warning(
                    "Could not save reference encoding cache: %s",
                    exc,
                )

        return no_face_names

    # ------------------------------------------------------------------
    # Main sort loop
    # ------------------------------------------------------------------

    def sort_all(
        self,
        progress_callback: Callable[[int, int, str], None],
        cancelled: Callable[[], bool],
    ) -> dict[str, int]:
        """Sort all event photos into per-student output subfolders.

        Processes one image at a time to keep RAM usage low.  For each detected
        face in a photo the nearest student is identified; the photo is copied
        to every matched student folder (allowing group shots).  Photos with no
        match or no face are copied to ``_unmatched/``.

        Args:
            progress_callback: Called with ``(current, total, filename)`` after
                each image so the GUI can update its progress bar.
            cancelled: Zero-arg callable; returns True if the user has cancelled.

        Returns:
            Dict with keys ``total``, ``matched``, ``unmatched``, ``skipped``.
        """
        images = collect_event_images(self.events_folder)
        total = len(images)

        counts = {"total": total, "matched": 0, "unmatched": 0, "skipped": 0}

        self.logger.info("Starting sort — %d images found", total)

        for current, (image_path, event_name) in enumerate(images, start=1):
            if cancelled():
                self.logger.info("Sort cancelled by user at image %d/%d", current, total)
                break

            progress_callback(current, total, image_path.name)

            output_filename = build_output_filename(event_name, image_path.name)

            try:
                rgb_image = self._load_and_resize(image_path)
            except UnidentifiedImageError:
                self.logger.warning("Corrupted image, moving to _unmatched: %s", image_path.name)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1
                continue
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Could not open %s: %s — skipping", image_path.name, exc)
                counts["skipped"] += 1
                continue

            try:
                face_locations = face_recognition.face_locations(rgb_image)  # HOG — fast
                if not face_locations:
                    face_locations = face_recognition.face_locations(rgb_image, model="cnn")  # CNN fallback
                face_encodings = face_recognition.face_encodings(
                    rgb_image, face_locations, num_jitters=3, model="large"
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Face detection failed for %s: %s", image_path.name, exc)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1
                continue

            if not face_encodings:
                self.logger.info("No face detected: %s → _unmatched", image_path.name)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1
                continue

            matched_students: set[str] = set()
            for encoding in face_encodings:
                match = self._match_face(encoding)
                if match:
                    matched_students.add(match)

            if matched_students:
                for student_name in matched_students:
                    dest_folder = self.output_folder / student_name
                    safe_copy(image_path, dest_folder, output_filename, self.logger)
                    self.logger.info(
                        "Matched %s → %s", image_path.name, student_name
                    )
                counts["matched"] += 1
            else:
                self.logger.info("No match: %s → _unmatched", image_path.name)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1

        self.logger.info(
            "Sort complete — total=%d matched=%d unmatched=%d skipped=%d",
            counts["total"],
            counts["matched"],
            counts["unmatched"],
            counts["skipped"],
        )
        return counts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_and_resize(self, image_path: Path) -> np.ndarray:
        """Open image with Pillow, resize if needed, and return as RGB numpy array.

        Resizing large images to at most MAX_IMAGE_DIMENSION on the longest side
        dramatically reduces face_locations() time on CPU without meaningfully
        reducing recognition accuracy.

        Raises:
            UnidentifiedImageError: If Pillow cannot read the file format.
        """
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            longest = max(width, height)
            if longest > self.MAX_IMAGE_DIMENSION:
                scale = self.MAX_IMAGE_DIMENSION / longest
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.LANCZOS)
            return np.array(img)

    def _match_face(self, encoding: np.ndarray) -> str | None:
        """Find the closest student encoding within DISTANCE_THRESHOLD.

        Uses face_distance() + argmin rather than compare_faces() booleans so
        each detected face always matches at most one student — the nearest one.

        Args:
            encoding: 128-d face encoding from face_recognition.

        Returns:
            Student name string if a match is found, otherwise None.
        """
        if not self._student_encodings:
            return None

        names = []
        known_encodings = []

        for student_name, student_encodings in self._student_encodings.items():
            names.extend([student_name] * len(student_encodings))
            known_encodings.extend(student_encodings)

        known_encodings_array = np.array(known_encodings)

        distances = face_recognition.face_distance(
            known_encodings_array, encoding
        )
        best_idx = int(np.argmin(distances))
        best_distance = distances[best_idx]

        if best_distance <= self.DISTANCE_THRESHOLD:
            self.logger.debug(
                "Face matched to %s (distance=%.4f)", names[best_idx], best_distance
            )
            return names[best_idx]

        self.logger.debug("No match — best distance=%.4f", best_distance)
        return None
