# Release Process

Padawan uses semantic versioning. Before 1.0, minor releases can still adjust
interfaces when the change is documented in this changelog and release notes.

## Release Artifacts

Each public release should publish:

```text
install-padawan.sh
install-padawan.ps1
padawan-wheelhouse.tar.gz
padawan-wheelhouse.zip
```

The wheelhouse archives include Padawan, dependency wheels, `INSTALL.txt`, and
`manifest.json`.

## First Release

The first wheelhouse release is `v0.1.0`. It marks Padawan's first public release
cycle and uses the existing package version:

```text
0.1.0
```

## Version Checklist

Before tagging a release:

1. Move changelog entries from `Unreleased` into `X.Y.Z - YYYY-MM-DD`.
2. Confirm `pyproject.toml`, `src/padawan/__init__.py`, and the app metadata use
   the same version.
3. Run:

   ```bash
   ruff check
   pytest
   padawan course validate --course all-seed
   ```

4. Commit with:

   ```bash
   git commit -m "Release vX.Y.Z"
   ```

5. Tag and push:

   ```bash
   git tag vX.Y.Z
   git push github dev
   git push github vX.Y.Z
   ```

The release workflow builds and uploads the installer and wheelhouse artifacts
from the tag.

## Manual Release Build

To build artifacts locally:

```bash
scripts/build_wheelhouse.sh --python .venv/bin/python
```

Artifacts are written to `dist/`.

## Rollback

If a release artifact is broken, create a patch release instead of replacing a
published artifact silently. Keep the broken release notes visible and point
users to the patch version.
