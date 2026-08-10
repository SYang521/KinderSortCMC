# KinderSort — Student Photo Organiser

[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/lerlerchan/KinderSort/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Offline](https://img.shields.io/badge/runs-offline-brightgreen?logo=shield&logoColor=white)](https://github.com/lerlerchan/KinderSort)
[![CPU Only](https://img.shields.io/badge/GPU-not_required-orange)](https://github.com/lerlerchan/KinderSort)
[![Release](https://img.shields.io/github/v/release/lerlerchan/KinderSort?color=blue&logo=github)](https://github.com/lerlerchan/KinderSort/releases)
[![Download EXE](https://img.shields.io/badge/download-.exe-success?logo=windows)](https://github.com/lerlerchan/KinderSort/releases)

[中文说明 (简体)](README.zh-CN.md)

KinderSort is an offline desktop app for kindergarten teachers. It scans event photos, matches student faces, and copies each photo into the correct student folder automatically — no internet connection, no coding knowledge required.

---

## Highlights

| Feature | Detail |
|---|---|
| Fully offline | No cloud upload, no internet required |
| CPU-only | Works on any Windows PC without a GPU |
| Simple GUI | Point-and-click, no terminal needed |
| Group photo support | One photo copied to all matched students |
| Safe operation | Files are **copied**, never moved or deleted |
| Audit trail | Detailed log written to `kindersort_log.txt` |

---

## Who this is for

- Teachers who need to organise large batches of student photos quickly
- Schools that require local/offline processing for privacy

---

## Quick Start (Teachers)

1. Download `KinderSort.exe` from the [**Releases**](https://github.com/lerlerchan/KinderSort/releases) page
2. Double-click `KinderSort.exe` — no installation needed
3. Select the three folders (Reference / Events / Output)
4. Click **Start Sorting**
5. Review the summary and open the Output folder

Full illustrated teacher guide: [`guidebook.md`](guidebook.md)

---

## Screenshot Walkthrough

| Step | Screenshot |
|---|---|
| 1. App launch | ![KinderSort launch](guidebook_assets/01_launch.png) |
| 2. Reference folder selected | ![Reference folder selected](guidebook_assets/02_reference_selected.png) |
| 3. Events folder selected | ![Events folder selected](guidebook_assets/03_events_selected.png) |
| 4. All folders ready | ![All folders set](guidebook_assets/04_all_folders_set.png) |
| 5. Sorting in progress | ![Sorting in progress](guidebook_assets/05_sorting_in_progress.png) |
| 6. Sorting complete | ![Sorting complete](guidebook_assets/06_sorting_complete.png) |
| 7. Timer display during sorting | ![Sorting with timer](guidebook_assets/07_timerInclude.png) |

---

## Folder Setup

You choose three folders inside the app:

1. **Reference Photos** — one clear front-facing photo per student, file name = student name
   ```
   reference/
     Ali.jpg
     Siti.png
     Kumar.jpeg
   ```

2. **Events Folder** — subfolders of mixed event photos
   ```
   events/
     Sports_Day/
     Concert/
     Field_Trip/
   ```

3. **Output Folder** — where sorted results are written

---

## Output Structure

```text
Output/
  Ali/
    Sports_Day__IMG_001.jpg
    Concert__IMG_045.jpg
  Siti/
    Sports_Day__IMG_001.jpg    ← same photo, Siti was also in it
    Field_Trip__IMG_023.jpg
  _unmatched/
    blurry_photo.jpg
    no_face_detected.jpg
  kindersort_log.txt
```

---

## Important Behaviour

- Face matching threshold is `0.55` (strict — minimises false positives)
- Photos are **copied**, not moved — originals are always safe
- Photos placed directly in the Events root (no subfolders) are also supported — the folder name is used as the event name
- If a reference photo has no detectable face, that student is skipped with a warning
- v1.1 uses higher-accuracy face recognition (CNN + multi-jitter) — sorting 500 photos typically takes **8–15 minutes** on a standard PC; the spinning timer shows progress so the app will not appear frozen

---

## Tech Stack

[![face_recognition](https://img.shields.io/badge/face__recognition-dlib-red)](https://github.com/ageitgey/face_recognition)
[![Pillow](https://img.shields.io/badge/Pillow-image_processing-yellow)](https://python-pillow.org/)
[![tkinter](https://img.shields.io/badge/tkinter-GUI-lightblue)](https://docs.python.org/3/library/tkinter.html)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-packaging-purple)](https://pyinstaller.org/)

| Component | Library |
|---|---|
| Face recognition | `face_recognition` + `dlib` |
| Image handling | `Pillow` |
| GUI | `tkinter` (built-in) |
| Packaging | `PyInstaller` |
| Language | Python 3.10+ |

---

## Developer Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Build Windows executable:

```bash
pyinstaller --onefile --windowed --name "KinderSort" main.py
# Output: dist/KinderSort.exe
```

## Multiple Reference Photos per Identity

This enhancement allows each identity to use multiple local reference photos. Different views, lighting conditions, and environments may provide additional face encodings for comparison.

### Supported folder structures

The original single-file structure remains supported for backwards compatibility:

    Reference_Photos/
      person_001.jpg
      person_002.jpg

The new folder-based structure supports multiple reference photos for each identity:

    Reference_Photos/
      person_001/
        front.jpg
        side.jpg
        indoor.jpg
      person_002/
        front.jpg
        side.jpg

Folder names and legacy file names represent identity labels. Anonymous identifiers such as person_001 should be used instead of real student names.

### Recognition workflow

1. KinderSort scans legacy image files and identity folders in the reference directory.
2. Each valid reference face is converted into a separate face encoding.
3. All encodings for the same identity are retained rather than overwritten.
4. A detected event-photo face is compared with every stored reference encoding.
5. The identity belonging to the smallest face distance is selected only when the distance is at or below the existing 0.55 threshold.
6. Results remain available for human review.

The original offline processing, CPU-only operation, Windows support, and event-image resizing behaviour are preserved. This enhancement does not require a GPU, cloud service, external API, or internet connection.

### Reference image validation

- A reference image with no detectable face is skipped and logged.
- A damaged or unreadable reference image is logged without stopping other images from being processed.
- If multiple faces are detected in one reference image, a warning is logged and only the first detected face is used.
- Logs include the anonymous identity label and relative reference path to support local investigation.
- An invalid image for one identity does not prevent other valid images for that identity from being loaded.
### Privacy and ethical safeguards

- Keep all children's photos, reference photos, ground-truth files, benchmark inputs, and output folders on the local device.
- Do not upload private face images or benchmark data to GitHub, cloud storage, or external APIs.
- Use anonymous identity labels instead of real names.
- Treat automated sorting as decision support rather than a final decision. A responsible adult should review unmatched and potentially incorrect results.
- Restrict access to local logs because file paths and identity labels may still contain sensitive information.

### Accuracy, fairness, and error risks

Multiple reference photos may reduce false negatives when a person appears under different angles or lighting conditions. However, improvement is not guaranteed for every identity.

Unequal reference coverage can create unfair performance differences. An identity with several clear and varied reference photos may be easier to recognise than an identity with only one low-quality image. Reference-photo quantity, image quality, pose, lighting, occlusion, and camera conditions should therefore be reviewed across identities.

A false positive assigns a photo to the wrong identity and creates a privacy risk because a child's photo may be copied into another person's folder. A false negative leaves a valid identity unmatched and may cause photos to be missed. The matching threshold must not be relaxed without measuring both risks on the same benchmark dataset.

Benchmark comparisons must use the same private images and ground truth before and after the enhancement. Report exact-match accuracy, unmatched cases, wrong-identity cases, processing time, CPU usage, RAM usage, and GPU usage. Private benchmark files must remain outside the public repository.
