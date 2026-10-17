# Tiny File Manager 3.0.0

This is the `fun-ed` maintenance fork of [prasathmani/tinyfilemanager](https://github.com/prasathmani/tinyfilemanager). Upstream history and the GPL license are retained. See [the issue assessment and maintenance plan](docs/issue-plan.md) for scope, verification results and remaining risks. This fork is not a claim of safe unrestricted public deployment.

The first maintained release is [3.0.0](https://github.com/fun-ed/tinyfilemanager/releases/tag/3.0.0). Read [CHANGELOG.md](CHANGELOG.md) before upgrading: the major version reflects stricter URL-upload, chunk-upload and configuration-write contracts, not a rewrite or a new production runtime. The live demo, donations and contributor links below belong to upstream.

[![Live demo](https://img.shields.io/badge/Live-Demo-brightgreen.svg?style=flat-square)](https://tinyfilemanager.github.io/demo/)
[![Live demo](https://img.shields.io/badge/Help-Docs-lightgrey.svg?style=flat-square)](https://github.com/prasathmani/tinyfilemanager/wiki)
[![GitHub Release](https://img.shields.io/github/v/release/fun-ed/tinyfilemanager?style=flat-square)](https://github.com/fun-ed/tinyfilemanager/releases)
[![GitHub License](https://img.shields.io/github/license/fun-ed/tinyfilemanager.svg?style=flat-square)](LICENSE)
[![Paypal](https://img.shields.io/badge/Donate-Paypal-lightgrey.svg?style=flat-square)](https://www.paypal.me/prasathmani)
![GitHub Sponsors](https://img.shields.io/github/sponsors/prasathmani)

> TinyFileManager is a versatile web-based PHP file manager designed for simplicity and efficiency. This lightweight single-file PHP application can be effortlessly integrated into any server directory, allowing users to store, upload, edit, and manage files and folders directly through their web browser.
TinyFileManager supports multiple languages and per-user directory settings. Runtime compatibility for this fork is recorded in the maintenance plan rather than inferred from the upstream PHP 5.5 claim.
Featuring syntax highlighting for over 150 languages and more than 35 themes, TinyFileManager offers a comprehensive solution for file management in an online environment.

<sub>**Caution!** _Avoid utilizing this script as a standard file manager in public spaces. It is imperative to remove this script from the server after completing any tasks._</sub>

## Demo

[Demo](https://tinyfilemanager.github.io/demo/)


## Documentation

Tinyfilemanager is highly documented on the [wiki pages](https://github.com/prasathmani/tinyfilemanager/wiki).

[![Tiny File Manager](screenshot.gif)](screenshot.gif)

## Requirements

- PHP with sessions. See the maintenance plan for the versions actually verified.
- Fileinfo, iconv, zip, Phar and mbstring support are recommended for their corresponding features.
- URL upload requires the PHP cURL extension. There is no stream-wrapper fallback.

## How to use

Download [release 3.0.0](https://github.com/fun-ed/tinyfilemanager/releases/tag/3.0.0), or its named ZIP and checksum assets. Put `tinyfilemanager.php` and `translation.json` together in the intended application directory. Keep managed data outside the public web root and use authenticated downloads rather than exposing the whole repository or uploads as static files. The PHP entry file may be renamed, but keep the catalog available to its working directory.

Default username/password: **admin/admin@123** and **user/12345**.

Replace the bundled credentials in `$auth_users` before use. Passwords must be stored with `password_hash()`. Use the authenticated application's Help page to generate a new hash locally; do not enter passwords into third-party hash-generation websites.

To enable/disable authentication set `$use_auth` to true or false.

:information_source: Add your own configuration file [config.php](https://tinyfilemanager.github.io/config-sample.txt) in the same folder to use as additional configuration file.

:information_source: To work offline without CDN resources, use [offline](https://github.com/prasathmani/tinyfilemanager/tree/offline) branch

### :loudspeaker: Features

- :cd: **Open Source:** Lightweight, minimalist, and extremely simple to set up.
- :iphone: **Mobile Friendly:** Optimized for touch devices and mobile viewing.
- :information_source: **Core Features:** Easily create, delete, modify, view, download, copy, and move files.
- :arrow_double_up: **Advanced Upload Options:** Ajax-powered uploads with drag-and-drop support, URL imports, and multi-file uploads with extension filtering.
- :file_folder: **Folder & File Management:** Create and organize folders and files effortlessly.
- :gift: **Compression Tools:** Compress and extract files in `zip` and `tar` formats.
- :sunglasses: **User Permissions:** User-specific root folder mapping and session-based access control.
- :floppy_disk: **Direct URLs:** Easily copy direct URLs for files.
- :pencil2: **Code Editor:** Includes Cloud9 IDE with syntax highlighting for 150+ languages and 35+ themes.
- :page_facing_up: **Document Preview:** Google/Microsoft document viewer for PDF/DOC/XLS/PPT, supporting previews up to 25 MB.
- :zap: **Security Features:** Backup capabilities, IP blacklisting, and whitelisting.
- :mag_right: **Search Functionality:** Use `datatable.js` for fast file search and filtering.
- :file_folder: **Customizable Listings:** Exclude specific folders and files from directory views.
- :globe_with_meridians: **Multi-language Support:** Translations available in 35+ languages with `translation.json`.
- :bangbang: **And Much More!**

### [Deploy by Docker](https://github.com/prasathmani/tinyfilemanager/wiki/Deploy-by-Docker)

### <a name=license></a>License, Credit

- Available under the [GNU license](https://github.com/prasathmani/tinyfilemanager/blob/master/LICENSE)
- Original concept and development by github.com/alexantr/filemanager
- CDN Used - _jQuery, Bootstrap, Font Awesome, Highlight js, ace js, DropZone js, and DataTable js_
- To report a bug or request a feature, please file an [issue](https://github.com/prasathmani/tinyfilemanager/issues)
- [Contributors](https://github.com/prasathmani/tinyfilemanager/wiki/Authors-and-Contributors)

## Maintainer checks

```sh
mise exec -- php -l tinyfilemanager.php
mise exec -- python3 tests/pr_regressions.py
mise exec -- php tests/security_helpers.php
git diff --check
```

The tests use disposable files, not your managed data. Project-local maintenance instructions are in `AGENTS.md`, `.agents/skills/tinyfilemanager-maintenance/SKILL.md`, and `.omp/agents/tinyfilemanager-maintainer.md`. No global agent installation is required.

Settings saves atomically replace configuration content and require a writable containing directory and a replaceable file. The active single-file `config.php` bind mount in Compose cannot be replaced this way: edit it on the host, disable the optional mount, or deploy a writable application directory instead. Failed saves report an error rather than truncating the file.

## URL-upload policy

URL upload is retained with a fail-closed downloader. Only HTTP and HTTPS on their default ports are allowed. Credentials in URLs, non-public or mixed public/private DNS answers, and redirects are rejected. Connections use a validated, pinned address, bypass proxy environment settings and retain TLS verification. cURL transfers have a 10-second connection timeout, a 60-second total timeout, and a streamed byte limit of the configured upload limit or 100 MiB, whichever is smaller. Synchronous DNS resolution follows host-resolver timeouts, not the cURL transfer timeout. URLs are limited to 4096 characters; DNS names must be ASCII without a trailing dot.

A rejection is an error, not a reason to retry through an unrestricted transport. Sites requiring redirects or non-default ports are not supported by this first safety policy. Other file-operation containment and deployment risks remain; see the maintenance plan.

For a recommendation-only comparison of production runtimes, see [FrankenPHP, RoadRunner and optional Caddy](docs/runtime-recommendation.md). The checked-in legacy PHP development-server image is not that proposed production deployment.
