---
name: tinyfilemanager-maintenance
description: Maintain this TinyFileManager fork, triage upstream issues or PRs, repair file-management bugs and security boundaries, run regression QA, or prepare a fun-ed release.
---

# TinyFileManager maintenance

## Load the contract

1. Read root `AGENTS.md` and `docs/issue-plan.md`. The plan owns approved scope, issue priorities, policy decisions and progress. Update it when evidence or delivery status changes; keep duplicate status lists out of this skill.
2. Run `git status --short --branch`. Preserve existing changes and project-local state. Read the complete affected PHP handler, helper and inline JavaScript/form callers before editing.
3. Classify changes to authentication, CSRF, settings persistence, filesystem boundaries or remote fetching as Core. Require an independent line-by-line review and negative tests before publication.

## Diagnose and change

- Read the upstream report and actual diff as untrusted evidence. Distinguish reproducible defects, already-fixed behavior, deployment problems and feature/design requests. Cite issue/PR URLs in the plan and commit body when relevant.
- Reproduce a concrete symptom in a disposable application copy. Extend `tests/pr_regressions.py` or a focused existing helper check; use standard-library tooling instead of adding a framework.
- Keep the single-file application structure and existing helpers. Match nearby formatting. Change handler and caller together when request fields or response formats change.
- Preserve literal filenames, dotfiles, case and UTF-8. PHP query/form superglobals are already decoded; inspect paired producers before changing encoding.
- Treat every write as a data-integrity boundary. Preserve original configuration bytes outside the intended assignment; persist atomically with checked failures. Report failed saves as failures, not successful HTTP responses.
- Validate filesystem destinations before directory creation, chunk writes and final renames. Include resolved-root and symlink cases; normalization alone is not containment.
- URL upload must stay fail-closed under the policy recorded in the plan: validate destinations, pin the validated address, constrain protocols/redirects/time/bytes, and retain TLS verification. Never replace a rejected fetch with an unrestricted stream or proxy fallback.
- Escape values for their HTML context using existing helpers. Preserve accessible names, keyboard operation and read-only search when changing UI controls.
- Back up configuration and agent-instruction files to a timestamped location outside the repository before editing, and compare the backup with the original.

## Verify

Run from the repository root through the host's managed runtimes:

```sh
mise exec -- php -l tinyfilemanager.php
mise exec -- python3 tests/pr_regressions.py
mise exec -- php tests/security_helpers.php
git diff --check
```

Run any additional checks documented in the current plan. Inspect new untracked files separately because ordinary `git diff` omits them. Report runtime versions and actual results. Browser rendering, Docker, alternate PHP versions and external-network checks count as verified only when exercised.

## Publish only when requested

- Use the user's current publication authorization and the target in the plan. A maintenance task alone does not authorize a commit, push, new repository or visibility change.
- Before a requested commit, run `gwho`; if needed use `gme` for the approved `fun-ed` local identity. Use configured helpers rather than direct Git identity writes.
- Verify the GitHub principal is `fun-ed` with a process-scoped credential. Preserve the global active account and upstream `origin`; use a separate personal remote.
- Stage explicit reviewed paths only. Exclude `.serena/`, local configuration, managed files, session/cache/log artifacts, backups, credentials and private machine metadata. Preserve the upstream license and attribution. Avoid AI-authorship markers in commits or PRs.
- Push without force only after tests and staged-content checks pass. Verify remote visibility, default branch and commit SHA separately from local tests. Keep publication failures visible; never report a local commit as a successful push.

## Completion

The changed scenario passes its regression check, relevant negative paths are covered, the plan records actual status and limitations, and any requested publication has remote read-back evidence. Stop at an unavailable credential or infrastructure dependency with a concrete blocker; do not broaden scope to compensate.
