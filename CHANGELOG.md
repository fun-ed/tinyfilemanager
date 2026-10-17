# Changelog

## 3.0.0 - 2026-10-17

First maintained release of the `fun-ed` fork after upstream 2.6. The major version marks deliberate security-contract changes; it does not imply a new framework, a production-runtime migration, or a complete security audit. Upstream history, authorship and the GPL license are retained.

### Security and data integrity

- Rotate both the session ID and CSRF token after successful login.
- Replace unrestricted URL-fetch streams with a cURL-only downloader. Validate all resolved destination addresses, pin the chosen address, reject private/reserved destinations and redirects, disable inherited proxies, and retain TLS verification.
- Restrict URL transfers to default-port HTTP/HTTPS with 10-second connection and 60-second cURL transfer timeouts, plus an actual streamed byte cap of the configured limit or 100 MiB, whichever is smaller.
- Make the validated uploaded filename authoritative instead of trusting `fullpath` to choose its extension. Check resolved upload roots before directory creation and block target/staging symlinks.
- Create chunk staging files exclusively, associate continuation with the session/upload identity and expected sequence, enforce accumulated limits, preserve existing partial files and dotfile names, and recover safely after terminal failures.
- Preserve configuration content outside one supported `$CONFIG` string assignment. Use checked atomic replacement, preserve file mode, invalidate OPcache and report save failures. Ambiguous assignments and unsafe insertion locations fail without changing the original.
- Escape reviewed document-title, filename-attribute and symlink-text output. Avoid deprecated cURL cleanup warnings on PHP 8.5.
- Stop directing users to third-party password-hash websites; the authenticated local generator remains available.

### Bug fixes and UI/UX

- Report editor saves as successful only after an explicit server confirmation. Handle expired sessions and stale tokens without claiming unsaved content was written.
- Preserve literal plus signs, spaces and percent sequences through matched download/copy/rename/archive request paths.
- Treat `application/x-empty` as text so extensionless empty files can be edited.
- Use native 64-bit `filesize()` before the historical shell fallback.
- Use an accessible, keyboard-operable Advanced Search button with Bootstrap 5 end alignment. Keep search available to read-only users.
- Include PHP cURL, the health-check executable and translation catalog in the legacy Docker image. Exclude local/private files from its build context.

### Upgrade notes

- URL upload now requires PHP cURL. Non-default ports, credentials in URLs, redirects, non-public/mixed DNS results and unsupported hosts are rejected instead of fetched through an insecure fallback. URL names are ASCII-only without trailing dots, and URLs are capped at 4096 characters. Internationalized names require an explicitly supported future policy.
- DNS lookup is synchronous and follows host-resolver timeouts; the cURL deadline does not bound that earlier lookup. Configure and test DNS timeouts before production use.
- Custom chunk clients must send ordered Dropzone-compatible `dzuuid`, index and total metadata. Inspect abandoned partial files deliberately; existing regular `.part` files are never silently overwritten.
- Settings saves need a writable containing directory and an atomically replaceable file. A single-file `config.php` bind mount is not replaceable this way. Edit that file on the host or deploy a writable application directory; there is no truncating in-place fallback. Settings persistence needs PHP's 7+ tokenizer parse mode.
- Configurations with computed, duplicate or nested `$CONFIG` assignments are unsupported for UI persistence. A missing assignment before a `declare`/`namespace` prologue is rejected unchanged.
- Replace the bundled credentials, keep authentication enabled and keep managed data outside the public web root. General filesystem confinement outside the reviewed upload paths remains a separate risk.
- The Dockerfile still describes a legacy PHP 7.4 development-server recipe. Do not treat its build success as an endorsement of an EOL production runtime. [Production runtime guidance](docs/runtime-recommendation.md) recommends evaluating FrankenPHP classic mode with its built-in Caddy; no deployment or RAM/CPU benchmark was performed.

### Maintenance and verification

- Added a source-backed [issue assessment and implementation plan](docs/issue-plan.md), repository guidelines, a local maintenance skill/agent, and the October 2026 runtime comparison.
- PHP 8.5.11 syntax, helper fixtures and all 21 isolated HTTP regressions passed.
- Opt-in live checks passed public HTTPS download, streamed size rejection/cleanup and redirect rejection.
- Firefox checks covered rendered filename inertness, editor callbacks, read-only search, menu bounds and keyboard operation at actual CSS viewports 500 and 1280. Viewports 320/375 were not verified.
- The legacy image built locally; PHP 7.4.33 syntax/helper checks and cURL/zip/catalog checks passed in a read-only, network-disabled container. This is not a full PHP-version or production-deployment matrix.

Upstream PRs incorporated or adapted: [#1443](https://github.com/prasathmani/tinyfilemanager/pull/1443), [#1439](https://github.com/prasathmani/tinyfilemanager/pull/1439), [#1412](https://github.com/prasathmani/tinyfilemanager/pull/1412), [#988](https://github.com/prasathmani/tinyfilemanager/pull/988). Additional fixes address the confirmed portions of [#1415](https://github.com/prasathmani/tinyfilemanager/issues/1415), [#1246](https://github.com/prasathmani/tinyfilemanager/issues/1246), [#1271](https://github.com/prasathmani/tinyfilemanager/issues/1271), [#1341](https://github.com/prasathmani/tinyfilemanager/issues/1341), [#1098](https://github.com/prasathmani/tinyfilemanager/issues/1098), [#1099](https://github.com/prasathmani/tinyfilemanager/issues/1099), [#1356](https://github.com/prasathmani/tinyfilemanager/issues/1356) and [#1366](https://github.com/prasathmani/tinyfilemanager/issues/1366). The plan distinguishes completed work from unverified reports and deferred features.

Release tags in this fork do not automatically publish a Docker image. The inherited DockerHub workflow is manual-only, so publishing a GitHub Release cannot implicitly deploy or push a container.
