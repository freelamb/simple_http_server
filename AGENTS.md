# AGENTS.md

This file gives future maintainers and coding agents the context needed to work on this repository safely.

## Project Overview

`simple_http_server` is a small Python HTTP file server with directory browsing, downloads, and browser-based file uploads. The project is intentionally lightweight and currently centers on one implementation file:

- `simple_http_server.py`: request handler, upload handling, path translation, MIME detection, CLI parsing, and server startup.
- `Dockerfile`: container entrypoint that serves `/opt/data`.
- `.github/workflows/github-actions-test.yml`: lint-only CI across Linux, macOS, and Windows.
- `README.md`: user-facing usage notes and project status.

Treat this project as a temporary file-sharing tool for trusted environments. It should not be presented as a hardened public internet service unless authentication, upload limits, and stronger path/file validation are added.

## Current Behavior

- Runs with `python simple_http_server.py 8000`.
- Accepts `--bind/-b ADDRESS`; the current default is `127.0.0.1`.
- Serves files from the current working directory.
- Lists directories when no `index.html` or `index.htm` exists.
- Adds an HTML upload form to directory listings.
- Stores uploaded files in the requested directory after sanitizing the uploaded filename.
- Avoids overwriting existing files by appending `_` to the target filename.
- Does not limit upload size by default; `--max-upload-size MIB` can set an explicit limit.
- Uses Python standard library modules only.

## Important Implementation Notes

- `SimpleHTTPRequestHandler` implements `GET`, `HEAD`, and `POST`.
- `deal_post_data()` manually parses multipart upload bodies. Be careful when changing it; malformed input, missing headers, non-ASCII filenames, and large files need explicit coverage.
- `translate_path()` maps URL paths to the current working directory and strips query/fragment components.
- The server uses a threaded HTTP server so multiple requests can be handled concurrently.
- The project still contains compatibility code for Python 2, but the Dockerfile and GitHub Actions use Python 3.9.

## Safety And Security Priorities

When making changes, prioritize these issues first:

1. Sanitize uploaded filenames.
   Use only a safe basename, reject absolute paths, reject `..`, and avoid allowing path separators inside uploaded names.

2. Escape all user-controlled HTML output.
   Directory names, file names, upload result messages, and paths should be HTML-escaped before rendering.

3. Preserve safer network defaults.
   The default bind address is `127.0.0.1`; document `0.0.0.0` as an explicit LAN/public option.

4. Keep upload size behavior explicit.
   Large or slow uploads can exhaust disk, memory, or worker capacity. The default is currently unlimited; document any limit changes clearly and keep `--max-upload-size` behavior covered by tests.

5. Improve request robustness.
   Handle missing `Content-Type`, missing `content-length`, malformed multipart bodies, and interrupted uploads without crashing the server.

6. Consider concurrent serving.
   If multi-client support is needed, use `ThreadingHTTPServer` on Python 3 and keep Python 2 compatibility decisions explicit.

## Development Guidelines

- Keep the project dependency-free unless there is a strong reason to add packaging or test dependencies.
- Preserve the simple CLI experience.
- Prefer small, focused changes over broad rewrites.
- If Python 2 support is removed, update README, CI, and code comments in the same change.
- If public/network-facing behavior changes, update README and SECURITY.md.
- Do not silently change the served root directory behavior; users expect the current working directory to be served.
- Avoid introducing platform-specific behavior without checking Linux, macOS, and Windows implications.

## Testing Guidance

There is no dedicated test suite yet. For any behavior change, add focused tests if possible. Useful coverage areas:

- `translate_path()` rejects or neutralizes traversal attempts.
- Directory listing escapes special characters.
- Download responses include content type, length, and last-modified headers.
- Upload accepts normal files.
- Upload handles duplicate names predictably.
- Upload rejects unsafe filenames.
- Malformed upload requests return an error page instead of crashing.
- CLI parsing supports default port, custom port, `--bind`, and `--version`.

Before finishing a change, at minimum run:

```bash
python3 -m py_compile simple_http_server.py
```

If lint dependencies are available, also run:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

For server behavior changes, manually start the server from a temporary directory and verify directory listing, download, upload, and duplicate filename handling.

Run the unit tests with:

```bash
python3 -m unittest discover -s tests
```

## Documentation Maintenance

Keep these files aligned:

- `simple_http_server.py`: source version in `__version__`.
- `README.md`: English install, run, Docker, support status, and security caveats.
- `README.zh-CN.md`: Simplified Chinese translation of `README.md`; update it whenever the English README changes.
- `SECURITY.md`: supported versions and vulnerability contact.
- `.github/workflows/github-actions-test.yml`: supported Python versions and CI checks.
- GitHub Releases: version history and release notes.

Known documentation drift to address in future work:

- README says Python 2 and Python 3 are supported, while CI and Docker only exercise Python 3.9.

## Versioned Release Workflow

Treat every code change as versioned work unless the user explicitly says it is documentation-only and should not be released. Before finishing a code change, keep the release metadata aligned and prepare the release follow-through:

- Decide the next version number before committing. Do not reuse a version that has already been uploaded to PyPI.
- Update the source version in `simple_http_server.py` (`__version__`).
- Update the package version in `pyproject.toml`.
- Update `README.md`, `SECURITY.md`, and any other user-facing docs when behavior, install steps, security posture, or supported versions change.
- Run the required tests and packaging checks before release.
- Commit the code and documentation changes together for that version.
- Create and push a matching Git tag, preferably `vX.Y.Z`.
- Create a GitHub Release for the tag with concise user-facing release notes.
- Build and upload the PyPI package for the same version.
- Build and push Docker Hub images for the same version whenever there is a version update.
- Verify the package can be installed or at least that `twine check` passes before asking the user to publish.

When multiple issues are fixed in one session, keep each issue as a separate focused commit. If separate releases are requested or appropriate, each release must have its own version, tag, GitHub Release, PyPI package, and Docker Hub image.

## Release And Packaging Notes

The project is packaged for PyPI with `pyproject.toml`. Keep the packaging metadata minimal and current:

- A console script entrypoint.
- README metadata.
- License metadata.
- Python version classifiers.
- A clear decision on Python 2 support.

Docker Hub image name: `yybmec/simple_http_server`. Every version update must push both `yybmec/simple_http_server:X.Y.Z` and `yybmec/simple_http_server:latest`, and keep the README Docker examples aligned with the published image.

The Docker Hub publish workflow requires repository secrets named `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. If those secrets are unavailable, document the manual Docker publish command and ask the maintainer to run it from a machine with Docker installed and Docker Hub access.

## Good First Improvements

- Add tests around path translation and upload filename safety.
- Sanitize and escape upload result output.
- Replace `HTTPServer` with a threaded server for Python 3.
- Update GitHub Actions to current action versions.
- Clarify safe usage in README.
