# Windows Deployment

## Release Overview

KinderSort Lite v1.2.0 is packaged as an offline, CPU-only Windows desktop
application. End users do not need Python, Visual Studio Code, a virtual
environment, or a dedicated GPU.

The deployment process uses:

- Python 3.11.9
- PyInstaller 6.22.0
- Inno Setup 6.7.3
- Windows x64-compatible packaging

## Build Dependencies

Install the application dependencies and deployment tools inside a Python
virtual environment.

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
```

The successfully tested Windows build environment used:

- `face-recognition==1.3.0`
- `dlib==19.24.1`
- `Pillow==10.3.0`
- `numpy==1.26.4`
- `PyInstaller==6.22.0`

The repository currently lists `dlib==19.24.2` in `requirements.txt`, while the
successfully tested Windows environment used a local CPython 3.11 x64 wheel for
dlib 19.24.1. A clean build environment should resolve and document this
version difference before public release.

## PyInstaller Build

KinderSort Lite uses an `onedir` build because large dependencies such as
dlib, NumPy, face-recognition models, Pillow, Tcl, and Tk do not need to be
extracted from a single executable every time the application starts.

Build the application with:

```powershell
python -m PyInstaller --clean --noconfirm KinderSort-onedir.spec
```

The result is created under:

```text
dist\KinderSort\
```

The primary executable is:

```text
dist\KinderSort\KinderSort.exe
```

The tested onedir build contained:

- Approximately 207.18 MB
- 1,008 files
- A 6.55 MB application executable
- dlib Windows binary
- face-recognition model files
- NumPy
- Pillow
- Tcl/Tk runtime files
- Tkinter

The following face-recognition resources were confirmed:

```text
dlib_face_recognition_resnet_model_v1.dat
mmod_human_face_detector.dat
shape_predictor_5_face_landmarks.dat
shape_predictor_68_face_landmarks.dat
```

## Inno Setup Build

Inno Setup 6.7.3 was installed from the official WinGet package:

```powershell
winget install --id JRSoftware.InnoSetup --exact --source winget --scope user
```

Compile the Installer with:

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" `
    "installer\KinderSortLite.iss"
```

The resulting Installer is:

```text
release\KinderSortLiteSetup.exe
```

## Installer Metadata

The validated Installer metadata is:

```text
Product name: KinderSort Lite
Product version: 1.2.0
File version: 1.2.0.0
Description: Offline CPU-only student photo organiser
```

The tested Installer size was:

```text
113,612,199 bytes
Approximately 108.35 MB
```

SHA-256:

```text
0F3371B6F8BF2C0FCC6D2723E2F3A2FEB2389E47EF6B0C95C25F39A529E15E01
```

The SHA-256 value applies only to the specific tested build. Rebuilding the
Installer may produce a different hash, which must be recalculated before
distribution.

## Installation Behaviour

KinderSort Lite uses a per-user installation by default and does not require
administrator privileges.

Default installation directory:

```text
%LOCALAPPDATA%\Programs\KinderSortLite
```

The Installer provides:

- Start Menu application shortcut
- Start Menu uninstall shortcut
- Optional desktop shortcut
- Complete uninstaller
- Application version metadata
- Local application installation

The desktop shortcut is optional and is not selected by default.

## Installed Application Validation

The installed executable was verified at:

```text
%LOCALAPPDATA%\Programs\KinderSortLite\KinderSort.exe
```

The installed GUI displayed:

```text
KinderSort Lite v1.2.0 - Student Photo Organiser
```

Measured installed GUI startup time:

```text
2.28 seconds
```

The unpacked onedir GUI startup time was:

```text
2.32 seconds
```

The Installer therefore introduced no meaningful startup delay during the
tested run.

## Functional Validation

The packaged application successfully processed a private 15-image dataset.

Results:

```text
Total images: 15
Matched: 9
Unmatched: 6
Skipped: 0
Runtime with Reference Cache: 2 minutes 40 seconds
```

These results were consistent with the source application and earlier packaged
application tests.

Private Reference photos, Event photos, Ground Truth data, generated Output,
logs, and local Cache files were not committed to GitHub.

## Image Format Validation

The installed application successfully opened and processed synthetic test
images in the following formats:

- JPEG
- PNG
- BMP
- WebP

All four synthetic images contained no faces and were copied to `_unmatched`
without errors or skipped files.

## Uninstallation and Privacy

The uninstaller removes:

- The installed application
- Application dependencies
- Start Menu shortcuts
- The application installation directory

The uninstaller asks the user whether locally stored Reference Encoding Cache
files should also be deleted.

The prompt explains that:

- Face encodings are sensitive biometric data.
- Cache files remain on the local Windows device.
- KinderSort Lite does not upload the Cache.
- Original Reference photos are not deleted.
- Event photos are not deleted.
- Output photos are not deleted.

The tested uninstallation produced these results:

```text
Application directory removed: Yes
KinderSort.exe removed: Yes
Start Menu shortcuts removed: Yes
Local Reference Cache removed: Yes
Existing Output folder preserved: Yes
```

Normal Cache deletion is application-level file deletion and does not guarantee
forensic erasure from SSD storage.

## Files Excluded from Source Control

The following deployment artifacts must not be committed:

```text
build\
dist\
release\
venv\
temp_dlib\
*.whl
Private Reference photos
Private Event photos
Ground Truth files
Generated Output
Application logs
Reference Encoding Cache files
```

Only reproducible build configuration, Installer scripts, source code, tests,
and documentation should be committed.

## Release Checklist

Before public release:

1. Pull the latest stable `main` branch.
2. Create a clean deployment branch.
3. Install the fixed build dependencies.
4. Run all automated tests.
5. Build the onedir application.
6. Inspect PyInstaller warnings.
7. Launch the packaged application.
8. Verify face-recognition model files.
9. Test JPEG, PNG, BMP, and WebP.
10. Compile the Inno Setup Installer.
11. Verify Installer metadata and SHA-256.
12. Test per-user installation.
13. Test Start Menu shortcuts.
14. Test optional desktop shortcut behaviour.
15. Launch the installed application.
16. Test sorting and Reference Cache reuse.
17. Test uninstallation.
18. Confirm user photos and Output remain untouched.
19. Test on Windows 10.
20. Test on Windows 11.
21. Test on a clean computer without Python or development tools.

## Remaining Validation

The Installer has been validated on the development computer. Before public
distribution, KinderSort Lite still requires testing on a clean Windows
computer that does not have:

- Python
- Visual Studio Code
- The repository
- The project virtual environment
- Preinstalled face-recognition dependencies

This clean-machine test is required to confirm that the Installer is fully
self-contained.

Windows 10 and Windows 11 should both be tested where suitable hardware is
available.