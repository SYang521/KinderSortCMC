"""Local reference encoding cache helpers for KinderSort."""

import hashlib
import os
from pathlib import Path
from typing import TypedDict

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