# Changelog

## Unreleased

- Synthetic orchestration tests for `train`, `evaluate` and `export` (TensorFlow and model
  I/O faked, no real photos or weights), raising full-`src` coverage from ~50% to 95%.
  CI now measures coverage with an explicit 80% floor and prints the report (#14).

- Hash-locked requirements for core, train and dev installs under `requirements/`, an offline
  guard (`scripts/check_install_pins.py`) and the re-locking guide in
  [docs/DEPENDENCY-LOCKS.md](docs/DEPENDENCY-LOCKS.md). The TensorFlow lock is pins only. The
  documented installs now use the locks. Pyproject floors are unchanged (#40).
