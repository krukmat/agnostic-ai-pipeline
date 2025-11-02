# Agent Prompt — Publish Medium Import Pages (v7-only)

**Goal:** Replace the repository `docs/` with the provided v7 pages (only), push to `main`, and output the Medium import URLs.

## Inputs
- ZIP file: `medium-pages-v7.zip` (contains `docs/index.html`, `docs/assets/`, and `docs/*-v7/index.html`).
- BASE_URL: `https://krukmat.github.io/agnostic-ai-pipeline`
- VERSION: `v7`

## Tasks
1. Remove any existing `docs/` from the repo.
2. Unzip `medium-pages-v7.zip` into the repository root (this creates `docs/`).
3. Commit and push the changes to branch `main`.
4. Generate a file `medium-import-urls-v7.txt` with the absolute URLs of each `docs/*-v7/` page:
   - Format: `<BASE_URL>/<slug>-v7/` (one per line).
5. Return the contents of `medium-import-urls-v7.txt` as the final output.

## Shell Hints
```bash
git rm -r docs || true
unzip medium-pages-v7.zip -d .

git add docs
git commit -m "docs: publish v7 only"
git push origin main

# Generate URL list (Linux/macOS)
BASE_URL="https://krukmat.github.io/agnostic-ai-pipeline"
find docs -maxdepth 1 -type d -name "*-v7" -printf "%f
" | sed "s|^|$BASE_URL/|; s|$|/|" > medium-import-urls-v7.txt
```

## Acceptance Criteria
- Only `docs/*-v7/`, `docs/assets/`, and `docs/index.html` exist in the repo.
- `medium-import-urls-v7.txt` lists 8 URLs (one per article).
- Pages render correctly and include hero images (thumbnails) when opened.
