# Repository Guidelines

## Project Overview

TinyFileManager is a browser-based PHP file manager for uploading, editing, downloading, and organizing server files. It is distributed primarily as one PHP script, not a framework application. The README warns against public exposure and recommends removing the script after use. Replace bundled credentials before deployment and keep authentication enabled.

## Architecture & Data Flow

- `tinyfilemanager.php` contains configuration defaults, session/authentication setup, action handlers, filesystem helpers, templates, CSS, and JavaScript. There is no separate API server or frontend build.
- Requests load defaults and optional adjacent `config.php`, initialize UI preferences and session state, validate authentication, normalize the requested `p` path, then handle actions before listing files and rendering a page. Paths use `FM_ROOT_PATH` and `FM_PATH`.
- Forms and inline jQuery/XMLHttpRequest callers share payload and response contracts with PHP branches. Change the handler and its caller together. Uploads use Dropzone chunking.
- Authentication, CSRF tokens, and flash messages use PHP sessions. Deployment settings use PHP variables and derived `FM_*` constants, not a dependency-injection container.
- `FM_Config` stores UI preferences in the JSON string `$CONFIG`. Saving atomically replaces one unambiguous top-level string assignment, or inserts one in a supported file, preserving unrelated bytes. It targets readable `config.php`, otherwise the application file. A writable containing directory is required; single-file bind mounts cannot be atomically replaced. Unsupported or failed writes return an error without truncating the original. Use a disposable copy for settings QA.

## Key Directories

Source lives at the repository root; there is no `src/` tree. `tests/pr_regressions.py` checks locally integrated PR fixes using disposable files and a temporary PHP server. `.github/workflows/` contains image-publishing automation. Compose mounts a local `data/` directory for managed files; use disposable contents for development.

## Development Commands

There is no dependency-install step or asset compilation.

```sh
php -S 127.0.0.1:8080                 # Open /tinyfilemanager.php
php -l tinyfilemanager.php            # PHP syntax check, not a test suite
mise exec -- python3 tests/pr_regressions.py  # Requires PHP CLI with Fileinfo
mise exec -- php tests/security_helpers.php   # Settings and URL/IP policy fixtures
docker build -t tinyfilemanager:local .
docker compose up --build            # Container app at http://localhost:8080/
```

Before using Compose, create a valid local `config.php` or disable its bind mount. The mount is active despite its misleading inline comment. Limit the configured file root to disposable data. The image runs PHP's development server; it is not a production web-server configuration.

## Code Conventions & Common Patterns

- Match nearby formatting, generally four-space indentation. Shared procedural helpers commonly use `fm_` snake_case names; constants use `FM_*`; classes include `FM_Config`, `FM_Zipper`, and `FM_Zipper_Tar`. Preserve the existing single-file structure.
- Action routing uses top-level conditionals. Page actions commonly set a session message and redirect; AJAX may return an HTTP error and terminate; uploads return JSON. Preserve the response format expected by the caller.
- Client-side asynchronous work uses callbacks and browser APIs. Keep changes within the existing inline scripts rather than adding a frontend framework or state library.
- Preserve authentication, read-only gates, CSRF checks, filename validation, and output escaping through helpers such as `verifyToken()` and `fm_enc()`. `fm_clean_path()` normalizes paths; it does not prove filesystem containment. Check root boundaries and symlinks in every affected operation.
- UI strings use `lng()`. Add English keys in that function and corresponding translations in `translation.json`; missing translations fall back to English.

## Important Files

- `tinyfilemanager.php` is the entry point and implementation. Search action names and helper symbols instead of relying on line numbers.
- `translation.json` holds language metadata and translations. Optional `config.php` overrides deployment defaults and is not checked in.
- `Dockerfile` copies the PHP entry point to `/var/www/html/index.php` and includes `translation.json`. It remains the legacy development-server recipe, not the recommended production runtime.
- `docker-compose.yml` defines ports, mounts, and health checking. `.github/workflows/PublishDocker.yml` is manual-only in this fork; pushing a release tag does not publish Docker images.
- `README.md` documents setup and links to the wiki; `SECURITY.md` defines vulnerability reporting.

## Runtime/Tooling Preferences

PHP is the application runtime. No Composer, npm, Bun, or Node dependency manifest or lockfile is checked in. The legacy Dockerfile uses `php:7.4-cli-alpine` and installs `zip` and `curl`; that image is not a compatibility test matrix. Settings persistence requires the PHP 7+ tokenizer parse mode, and this fork's verified runtime versions belong in `docs/issue-plan.md`. The production runtime recommendation is `docs/runtime-recommendation.md`; it does not authorize a migration.

Check extensions for the affected feature: Fileinfo, iconv, mbstring, ZipArchive, PharData, and cURL. URL uploads require PHP cURL and fail closed without it. The Dockerfile also installs the separate `curl` executable used by Compose health checking. UI assets use public CDNs; offline use requires separate asset provisioning. PHP upload/post/memory limits must also permit the configured upload size.

## Testing & QA

`tests/pr_regressions.py` uses Python's standard-library unittest and PHP CLI, without third-party packages. It covers authentication/CSRF, settings, filename encoding, multipart/chunk uploads, rejected URL targets, output escaping, and file sizes. It runs a temporary loopback server against a disposable application copy, not the working files. `tests/security_helpers.php` checks actual production policy/helpers and settings preservation fixtures. There is no coverage target, formatter, or lint configuration. The manual Docker workflow does not run these tests automatically. Run the PHP syntax check after PHP edits and validate `translation.json` with a JSON parser after catalog edits.

Manually exercise the changed operation against disposable files. For broad request-flow changes, cover login/logout, navigation, create/rename/copy/move/delete, upload/download, and editor save. Check archive operations when relevant. Security changes also need read-only, invalid-token, and out-of-root path cases. Report which checks ran and which runtime versions were actually exercised.

## Maintenance workflow

For upstream issue/PR triage, security fixes, or publication, read `docs/issue-plan.md` and `.agents/skills/tinyfilemanager-maintenance/SKILL.md`. The plan owns approved scope, progress and verification evidence. The project-local agent prompt is `.omp/agents/tinyfilemanager-maintainer.md`; load it explicitly if the current harness does not discover project agents. These files are repository-local, not global installations.
