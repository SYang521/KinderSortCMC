"""Local reference encoding cache helpers for KinderSort."""

from pathlib import Path
from typing import TypedDict


class ReferenceManifestEntry(TypedDict):
    """File metadata used to detect changed reference photos."""

    student_name: str
    relative_path: str
    size: int
    modified_ns: int


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