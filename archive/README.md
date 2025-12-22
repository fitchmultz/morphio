# Archive

This directory contains projects moved out of the repository root to reduce clutter and signal their deprecated/paused status.

## Moves

- morphio → archive/morphio
- morphio-gcp → archive/morphio-gcp

## When

- Local time: 2025-09-08 11:34 MDT
- UTC: 2025-09-08T17:34:15Z

## Why

These were not the active focus compared to `morphio-io` and `morphio-fastapi`.

## How to restore

From repo root, move a project back up:

```bash
mv archive/<project> ./
```

Or with git to preserve history (if tracked):

```bash
git mv archive/<project> ./
```

## Notes

- No references to `morphio/` or `morphio-gcp/` remained outside `archive/` at the time of the move.
- CI only targets the active projects; archived projects have no automated workflows.
