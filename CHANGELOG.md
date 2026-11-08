# Changelog

## Unreleased

- Hash-locked requirements for core, train and dev installs under `requirements/`, an offline
  guard (`scripts/check_install_pins.py`) and the re-locking guide in
  [docs/DEPENDENCY-LOCKS.md](docs/DEPENDENCY-LOCKS.md). The TensorFlow lock is pins only. The
  documented installs now use the locks. Pyproject floors are unchanged (#40).
