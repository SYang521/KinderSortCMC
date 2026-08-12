"""Local reference encoding cache helpers for KinderSort."""

import hashlib
import os
from pathlib import Path
from typing import TypedDict

APP_CACHE_DIRECTORY = "KinderSortLite"
CACHE_DIRECTORY = "cache"
METADATA_FILENAME = "metadata.json"
ENCODINGS_FILENAME = "encodings.npz"


class ReferenceManifestEntry(TypedDict):
    """File metadata used to detect changed reference photos."""

    student_name: str
    relative_path: str
    size: int
    modified_ns: int


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