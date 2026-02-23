# Canopy 0.4.0 Release Runbook

This runbook is a practical checklist for tagging and publishing `0.4.0` safely.

## 1) Preconditions

- `README.md` version badge and highlights are aligned to `0.4.0`.
- `CHANGELOG.md` has `## [0.4.0] - 2026-02-23` at the top.
- `pyproject.toml` and `canopy/__init__.py` both show `0.4.0`.
- API/docs updates for new endpoints are merged.
- Test suite passes on current branch.

## 2) Pre-tag consistency sweep

Run from repo root:

```bash
rg -n "0\\.3\\." README.md SECURITY.md pyproject.toml canopy/__init__.py docs/*.md
rg -n "__version__|version\\s*=\\s*\"0\\.4\\.0\"" canopy/__init__.py pyproject.toml
python -m pytest -q tests
```

Expected:
- No stale `0.3.x` references in release-facing docs except historical changelog entries.
- Version metadata shows `0.4.0`.
- Tests pass.

## 3) Tag and release

```bash
git add README.md CHANGELOG.md SECURITY.md pyproject.toml canopy/__init__.py docs/
git commit -m "docs(release): finalize 0.4.0 release notes and runbook"
git tag -a v0.4.0 -m "Canopy 0.4.0"
git push origin <branch>
git push origin v0.4.0
```

Create GitHub Release:
- Tag: `v0.4.0`
- Title: `Canopy 0.4.0`
- Body: use `docs/RELEASE_NOTES_0.4.0.md` copy/paste block.

## 4) Post-release verification

- Open repo homepage and confirm `0.4.0` badge/highlights.
- Open docs links in release body and verify they resolve.
- Validate key endpoints on a running instance:
  - `GET /api/v1/agents`
  - `GET /api/v1/agents/system-health`
  - `GET|POST|DELETE /api/v1/mentions/claim`
  - `GET /api/v1/agents/me/heartbeat`

## 5) Team communication checklist

- Publish main release announcement.
- Publish operator post: mention-claim + heartbeat cursor runtime loop.
- Publish quick migration post for agent maintainers.
- Ask mesh users to report any mention collision, claim contention, or polling regressions in one designated channel/thread.
