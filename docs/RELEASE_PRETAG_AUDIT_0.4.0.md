# Canopy 0.4.0 Pre-Tag Audit

Audit date: 2026-02-23

This file records pre-tag verification run on the current working tree.

## Commands executed

```bash
rg -n "0\\.3\\." README.md SECURITY.md pyproject.toml canopy/__init__.py \
  docs/QUICKSTART.md docs/API_REFERENCE.md docs/MENTIONS.md \
  docs/MCP_QUICKSTART.md docs/CONNECT_FAQ.md docs/PEER_CONNECT_GUIDE.md \
  docs/GITHUB_RELEASE_ANNOUNCEMENT_DRAFT.md docs/TEAM_ANNOUNCEMENT_0.4.0.md \
  docs/RELEASE_NOTES_0.4.0.md
rg -n "__version__\\s*=\\s*\"0\\.4\\.0\"|version\\s*=\\s*\"0\\.4\\.0\"" canopy/__init__.py pyproject.toml
for f in README.md docs/RELEASE_NOTES_0.4.0.md docs/TEAM_ANNOUNCEMENT_0.4.0.md docs/GITHUB_RELEASE_ANNOUNCEMENT_DRAFT.md; do
  echo "## $f"
  rg -o '\\[[^]]+\\]\\(([^)]+)\\)' "$f" \
  | sed -E 's/.*\\(([^)]+)\\).*/\\1/' \
  | grep -vE '^https?://' \
  | grep -vE '^#' \
  | while read -r link; do
      if [ -e "$link" ] || [ -e "$(dirname "$f")/$link" ]; then :; else echo "missing: $link"; fi;
    done;
done
python -m pytest -q tests
```

## Results

- Stale release-facing version references: pass.
  - No stale `0.3.x` markers in release-facing docs/metadata.
- Version metadata alignment: pass.
  - `canopy/__init__.py` -> `__version__ = "0.4.0"`
  - `pyproject.toml` -> `version = "0.4.0"`
- Local markdown link sanity for release artifacts: pass.
  - No missing local markdown links detected in checked files.
- Test suite: pass.
  - `60 passed` on `tests/`.

## Conclusion

Pre-tag checks for `0.4.0` are green for docs/version consistency and regression test baseline.
