# Privacy rules

This repository is public. It holds code only.

**Never commit:** photos (any format), model weights or TFLite files, label files that map photos to
labels, licence plates, GPS coordinates or EXIF, street addresses, names, e-mail addresses, keys,
tokens, or links to private systems.

**Where data lives:** training photos, labels and trained weights are kept in a separate private
location. Scripts take a `--data-dir` outside the checkout. Nothing in this repo uploads or logs images.

**Enforcement:**

- `tools/privacy_guard.py` runs in CI and fails the build on forbidden file types, binary files and
  text matching plate, GPS, address, e-mail, government URL or key patterns.
- `.gitignore` blocks image and model extensions.
- Tests use synthetic images generated in code only.
- Preprocessing re-encodes from pixels, so EXIF is dropped before any image is used.

The guard is a safety net, not a substitute for review. Check every PR for personal details,
including in issue and PR text.
