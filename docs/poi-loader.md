# POI Loader Operations Guide

This document explains how the POI loader scripts locate the project root and how to run them both locally and inside Kubernetes. The goal is to avoid path issues when your checkout lives in a directory such as `gorkycode` while the production containers use `/app`.

## Project Root Detection

Both loader scripts set the `PROJECT_ROOT` environment variable automatically when it is not provided. They delegate to `ensure_project_root` from `scripts/poi_loader_utils.py`, which inspects the current environment, optional hints, and then walks up from the script location until it finds a directory that contains either the `data/` or the `app/` folder. This means:

- In local development the root resolves to your checkout, for example `/home/user/gorkycode`.
- In containers built from our Dockerfiles the root resolves to `/app`.

The helper module `scripts/poi_loader_utils.py` also ensures that Python can import the generated gRPC stubs by adding the relevant directories (for example `app/proto`) to `sys.path` via `ensure_pythonpath`. Any custom value you export for `PROJECT_ROOT` is honoured when resolving `data/poi.json`.

You can still override the detection manually:

```bash
export PROJECT_ROOT=/custom/path/to/gorkycode
```

The loader will automatically look for the dataset at `${PROJECT_ROOT}/data/poi.json`.

## Running the Loader Locally

1. Ensure dependencies are available (for example, via Poetry or the service Docker image).
2. Export a database URL that points to your PostgreSQL instance.
3. Run the script from the repository root:

```bash
PROJECT_ROOT=$(pwd) \
DATABASE_URL=postgresql://user:pass@localhost:5432/aitourist_db \
python scripts/load_pois.py
```

The script now connects with `asyncpg.connect(DATABASE_URL)` without custom record classes, so a standard DSN works out of the box.

## Kubernetes Job

The Helm job template explicitly sets `PROJECT_ROOT=/app` for clarity. The POI loader container therefore behaves the same way it does in development, but you still have the option to override the root via environment variables if you ever change the container layout.

## Troubleshooting Tips

- If you see `ModuleNotFoundError: No module named 'poi_loader_utils'`, confirm that the `/scripts` directory is present in the container and that `PROJECT_ROOT` points at the directory containing `data/poi.json`.
- When the loader reports missing datasets, double-check that `${PROJECT_ROOT}/data/poi.json` is mounted or copied into the container.
- For path debugging you can print `os.environ['PROJECT_ROOT']` inside the loader scripts to verify which root was detected.

