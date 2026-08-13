# Low-Resource Optimization

## Reference Encoding Cache

KinderSort Lite stores previously generated reference face encodings in a local
cache. This avoids repeating the expensive reference face detection and
encoding process when the reference photos have not changed.

The optimization preserves the existing CPU-only and offline recognition
pipeline. No dedicated GPU, cloud service, or internet connection is required.

## Cache Behaviour

- The first run generates reference face encodings and saves them locally.
- Later runs load valid encodings directly from the cache.
- Adding, deleting, renaming, or modifying a reference photo invalidates the
  old cache.
- An invalid, incomplete, incompatible, or corrupted cache is rejected.
- KinderSort then rebuilds the cache from the current reference photos.
- Multiple reference photos for the same identity remain supported.
- Cache write failure does not prevent the current sorting operation from
  continuing with the encodings already held in memory.

## Local Storage

On Windows, the cache is stored under:

```text
%LOCALAPPDATA%\KinderSortLite\cache\<reference-folder-id>\
```

Each cache contains:

```text
metadata.json
encodings.npz
```

The reference folder ID is derived from a hash of the normalized folder path.
The folder name is not exposed in the cache directory name.

The NumPy cache contains numeric arrays only and is loaded with
`allow_pickle=False`.

## Privacy and Ethical Considerations

Face encodings are sensitive biometric data.

- Cache files remain on the user's Windows device.
- KinderSort does not upload the cache or reference photos.
- Cache data is not stored in the Events or Output folders.
- Cache files and private test photos must not be committed to the public
  repository.
- The GUI provides a **Clear Reference Cache** control.
- Clearing the cache deletes only `metadata.json` and `encodings.npz`.
- Original Reference photos, Event photos, and Output photos are not deleted.
- If deletion fails, KinderSort displays an explicit error instead of silently
  reporting success.

The clear operation performs normal application-level file deletion. It does
not claim to provide forensic erasure from SSD storage.

## Cache Invalidation

The Reference manifest records:

- Student identity
- Reference photo relative path
- File size
- Last-modified time

The cache metadata also records:

- Cache schema version
- Reference face-location model
- Number of encoding jitters
- Face encoding model
- Encoding dimension

A mismatch causes the cache to be rejected and rebuilt.

## Validation Results

Private test photos, Ground Truth files, generated Output, logs, and local cache
files were not committed to GitHub.

Test dataset:

- Total event images: 15
- Matched: 9
- Unmatched: 6
- Skipped: 0

### Cache Miss

- Total runtime: 6 minutes 2 seconds
- Reference encodings were generated from the source photos.
- The local cache was saved successfully.

### Cache Hit

- Total runtime: 2 minutes 39 seconds
- Four student identities were loaded from the local cache.
- Classification results remained unchanged.

### Observed Improvement

- Time saved: 3 minutes 23 seconds
- Runtime reduction: approximately 56.1%
- Cache-hit run was approximately 2.28 times as fast as the cache-miss run.

The observed improvement applies to this test dataset and computer. Performance
will vary with CPU speed, image dimensions, reference count, event-photo count,
storage performance, and antivirus scanning.

## Automated Tests

The automated test suite covers:

- Legacy single-photo references
- Folder-based multiple reference photos
- Reference file change detection
- Privacy-friendly cache paths
- Schema and encoding-configuration validation
- Missing and corrupted cache files
- Invalid encoding shapes
- Non-finite encoding values
- Non-object NumPy arrays
- Pickle-disabled loading
- Cache hit behaviour
- Cache miss and cache creation
- Stale cache rebuilding
- Privacy-safe cache clearing

Run the tests with:

```powershell
python -m unittest discover -s tests -v
```

At the time of validation, all 21 automated tests passed.

## Known Limitations

- File changes are detected using relative path, size, and last-modified time,
  rather than a full content hash.
- Clearing the cache causes the next sorting run to regenerate reference
  encodings.
- The cache improves reference loading time but does not reduce the time needed
  to process event photos.
- Cache files contain biometric encodings and should be protected using normal
  Windows account and device-security controls.
- Normal file deletion does not guarantee forensic erasure from SSD storage.