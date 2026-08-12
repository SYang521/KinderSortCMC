"""Local reference encoding cache helpers for KinderSort."""

import hashlib
import json
import os
from pathlib import Path
from typing import TypedDict

import numpy as np

APP_CACHE_DIRECTORY = "KinderSortLite"
CACHE_DIRECTORY = "cache"
METADATA_FILENAME = "metadata.json"
ENCODINGS_FILENAME = "encodings.npz"
CACHE_SCHEMA_VERSION = 1


class ReferenceManifestEntry(TypedDict):
    """File metadata used to detect changed reference photos."""

    student_name: str
    relative_path: str
    size: int
    modified_ns: int


class CacheMetadata(TypedDict):
    """Versioned metadata used to validate a local encoding cache."""

    schema_version: int
    reference_manifest: list[ReferenceManifestEntry]
    encoding_config: dict[str, object]


def build_cache_metadata(
    reference_manifest: list[ReferenceManifestEntry],
    encoding_config: dict[str, object],
) -> CacheMetadata:
    """Build versioned metadata for a reference encoding cache.

    Args:
        reference_manifest: Current reference photo file metadata.
        encoding_config: Face encoding parameters that affect cache contents.

    Returns:
        Metadata that can later be validated before loading encodings.
    """
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "reference_manifest": reference_manifest,
        "encoding_config": encoding_config,
    }


def is_cache_metadata_valid(
    metadata: object,
    current_manifest: list[ReferenceManifestEntry],
    current_encoding_config: dict[str, object],
) -> bool:
    """Return whether cache metadata matches the current inputs.

    Invalid, incomplete, outdated, or differently configured metadata is
    rejected so the caller can rebuild the cache instead of using stale face
    encodings.
    """
    if not isinstance(metadata, dict):
        return False

    return (
        metadata.get("schema_version") == CACHE_SCHEMA_VERSION
        and metadata.get("reference_manifest") == current_manifest
        and metadata.get("encoding_config") == current_encoding_config
    )


def save_reference_cache(
    metadata_path: Path,
    encodings_path: Path,
    metadata: CacheMetadata,
    student_encodings: dict[str, list[np.ndarray]],
) -> None:
    """Save metadata and multiple reference encodings locally.

    Student names are stored as Unicode arrays, and face encodings are stored
    as a numeric matrix. No Python object arrays or pickle data are used.

    Args:
        metadata_path: Destination path for versioned JSON metadata.
        encodings_path: Destination path for numerical NumPy data.
        metadata: Validated cache metadata to save.
        student_encodings: One or more face encodings for each student.

    Raises:
        ValueError: If no encodings exist or an encoding has an invalid shape.
    """
    names: list[str] = []
    encoding_rows: list[np.ndarray] = []

    for student_name in sorted(student_encodings):
        for encoding in student_encodings[student_name]:
            encoding_array = np.asarray(encoding, dtype=np.float64)
            if encoding_array.shape != (128,):
                raise ValueError(
                    "Each reference encoding must contain 128 values."
                )

            if not np.all(np.isfinite(encoding_array)):
                raise ValueError(
                    "Reference encodings must contain only finite values."
                )

            names.append(student_name)
            encoding_rows.append(encoding_array)

    if not encoding_rows:
        raise ValueError("Cannot save an empty reference encoding cache.")

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    encodings_path.parent.mkdir(parents=True, exist_ok=True)

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    np.savez_compressed(
        encodings_path,
        student_names=np.asarray(names, dtype=np.str_),
        encodings=np.vstack(encoding_rows),
    )


def load_reference_cache(
    metadata_path: Path,
    encodings_path: Path,
    current_manifest: list[ReferenceManifestEntry],
    current_encoding_config: dict[str, object],
) -> dict[str, list[np.ndarray]] | None:
    """Load and validate locally cached reference encodings.

    Pickle loading is disabled. Missing, outdated, malformed, or corrupted
    cache data is rejected so the caller can rebuild it safely.

    Args:
        metadata_path: Path to the versioned JSON metadata.
        encodings_path: Path to the numerical NumPy cache.
        current_manifest: Current reference photo file metadata.
        current_encoding_config: Current face encoding parameters.

    Returns:
        Encodings grouped by student name, or None when the cache is invalid.
    """
    if not metadata_path.is_file() or not encodings_path.is_file():
        return None

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )

        if not is_cache_metadata_valid(
            metadata,
            current_manifest,
            current_encoding_config,
        ):
            return None

        with np.load(encodings_path, allow_pickle=False) as cache_data:
            if set(cache_data.files) != {"student_names", "encodings"}:
                return None

            student_names = cache_data["student_names"]
            encodings = cache_data["encodings"]

        if student_names.ndim != 1:
            return None

        if student_names.dtype.kind not in {"U", "S"}:
            return None

        if encodings.ndim != 2 or encodings.shape[1] != 128:
            return None

        if len(student_names) != len(encodings):
            return None

        if len(student_names) == 0:
            return None

        if not np.issubdtype(encodings.dtype, np.number):
            return None

        if not np.all(np.isfinite(encodings)):
            return None

        loaded_encodings: dict[str, list[np.ndarray]] = {}

        for student_name, encoding in zip(
            student_names.tolist(),
            encodings,
            strict=True,
        ):
            name = str(student_name)

            if not name:
                return None

            loaded_encodings.setdefault(name, []).append(
                np.asarray(encoding, dtype=np.float64)
            )

        return loaded_encodings

    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def build_cache_paths(
    reference_folder: Path,
    local_app_data: Path,
) -> tuple[Path, Path]:
    """Build stable local cache paths without exposing the folder name.

    The reference folder path is normalized and hashed so different reference
    folders receive separate cache locations. The function only calculates
    paths and does not create directories or files.

    Args:
        reference_folder: Root folder selected for reference photos.
        local_app_data: Windows local application data directory.

    Returns:
        Paths for the cache metadata and numerical face encodings.
    """
    normalized_reference_path = os.path.normcase(
        str(reference_folder.resolve())
    )
    reference_id = hashlib.sha256(
        normalized_reference_path.encode("utf-8")
    ).hexdigest()[:24]

    cache_folder = (
        local_app_data
        / APP_CACHE_DIRECTORY
        / CACHE_DIRECTORY
        / reference_id
    )

    return (
        cache_folder / METADATA_FILENAME,
        cache_folder / ENCODINGS_FILENAME,
    )


def build_reference_manifest(
    reference_folder: Path,
    reference_images: list[tuple[str, Path]],
) -> list[ReferenceManifestEntry]:
    """Build stable metadata for legacy and folder-based reference photos.

    The manifest stores only local file metadata. It does not contain image
    content or face encodings.

    Args:
        reference_folder: Root folder selected for reference photos.
        reference_images: Student names paired with their reference image paths.

    Returns:
        Manifest entries sorted by relative path and student name.

    Raises:
        ValueError: If a reference image is outside reference_folder.
        FileNotFoundError: If a reference image no longer exists.
    """
    reference_root = reference_folder.resolve()
    manifest: list[ReferenceManifestEntry] = []

    for student_name, image_path in reference_images:
        resolved_path = image_path.resolve()

        try:
            relative_path = resolved_path.relative_to(reference_root)
        except ValueError as exc:
            raise ValueError(
                f"Reference image is outside the selected folder: {image_path}"
            ) from exc

        file_stat = resolved_path.stat()
        manifest.append(
            {
                "student_name": student_name,
                "relative_path": relative_path.as_posix(),
                "size": file_stat.st_size,
                "modified_ns": file_stat.st_mtime_ns,
            }
        )

    return sorted(
        manifest,
        key=lambda entry: (
            entry["relative_path"].casefold(),
            entry["student_name"].casefold(),
        ),
    )