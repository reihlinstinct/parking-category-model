# Dependency locks (#40)

Every documented install reads a lock under `requirements/`, so a changed or
substituted package fails the install instead of running. The pattern follows
parking-report-helper #177, scaled down to this repo.

## The locks

| Lock | Generated from | Hashes |
|---|---|---|
| `requirements/build.txt` | `requirements/build.in` (= `[build-system] requires`) | sha256 |
| `requirements/core.txt` | `pyproject.toml` `dependencies` | sha256 |
| `requirements/dev.txt` | `pyproject.toml` `dependencies` + `dev` extra, constrained by `core.txt` | sha256 |
| `requirements/train.txt` | `pyproject.toml` `dependencies` + `train` extra, constrained by `core.txt` | none, `==` pins only |

All four are universal resolutions for Python 3.11 and newer
(`uv pip compile --universal --python-version 3.11`): one file per lock, with environment markers where a
package differs by Python version (numpy 2.5 needs Python 3.12, so 3.11 gets
the newest 2.4 release). The floors in `pyproject.toml` are the only inputs;
each lock pins the newest versions that satisfy them.

`requirements/lock-evidence.json` records, per lock, the generating command,
a digest of its inputs (the `pyproject.toml` sections, `.in` file and
constraint lock it reads) and a digest of the lock itself.

### Why the TensorFlow lock has no hashes

TensorFlow publishes no wheel for CPython 3.14 (the newest stable release has
`cp310` to `cp313` wheels only, and there is no source distribution), while
the project supports 3.11 to 3.14. The maintainer's rule for #40 is that the
`train` extra is then pinned with `==` only. Its install uses
`pip install --no-deps -r requirements/train.txt`, so nothing outside the
pins is installed. Training therefore needs Python 3.11 to 3.13 until a stable
TensorFlow release ships `cp314` wheels; the tests and lint (core + dev) work
on every supported Python.

## Install

```bash
pip install --require-hashes -r requirements/build.txt -r requirements/dev.txt
pip install --no-deps --no-build-isolation -e ./
pip install --no-deps -r requirements/train.txt   # training only
```

The project installs with no dependency resolution and no build isolation,
after the pinned build prerequisites, so every package on the machine came
from a lock.

## Re-locking

After changing a floor in `pyproject.toml` (or `[build-system] requires`, and
then `requirements/build.in` to match), regenerate every lock with the
command in its header, from the repository root, then re-record the evidence:

```bash
uv pip compile --universal --generate-hashes --python-version 3.11 requirements/build.in -o requirements/build.txt
uv pip compile --universal --generate-hashes --python-version 3.11 pyproject.toml -o requirements/core.txt
uv pip compile --universal --generate-hashes --python-version 3.11 pyproject.toml --extra dev -c requirements/core.txt -o requirements/dev.txt
uv pip compile --universal --python-version 3.11 pyproject.toml --extra train -c requirements/core.txt -o requirements/train.txt
python scripts/check_install_pins.py --write-evidence
python scripts/check_install_pins.py
```

Add the --upgrade option to the compile commands to move to newer releases on
purpose. Commit the locks and the evidence file together.

## The guard

`scripts/check_install_pins.py` (standard library only, offline; tests in
`tests/test_install_pins.py`) fails on:

- an install command in tracked Markdown (fenced code and inline code),
  a Dockerfile `RUN` or a workflow `run:` step that installs by name, by URL,
  unpinned, from a file that is not one of the locks, from a hashed lock
  without --require-hashes, from the pins-only lock without --no-deps, or the
  local project without --no-deps --no-build-isolation; pip,
  `python -m pip` with global options, pip3.X, `uv pip`, `uv tool`, pipx and
  easy_install are all recognised, as is an installer behind a variable;
- a lock line that is not an exact `==` pin, a hashed lock pin without a
  sha256 hash, a header that does not show the generating command, a
  top-level requirement outside its `pyproject.toml` floor, a pin that
  disagrees with the core lock, `requirements/build.in` drifting from
  `[build-system] requires`, and a lock or input that changed without new
  evidence.

## Workflows

The workflows under `.github/` are changed by the maintainer, not in
contributor PRs. Until the hashed install lands there,
`requirements/pending-workflow-installs.json` names the two remaining
`ci.yml` install lines by path, line and command. The guard reports them as
pending instead of failing, fails when an entry stops matching a violating
line, and accepts only `.github/workflows/` paths. The workflow change
deletes the file in the same commit.
