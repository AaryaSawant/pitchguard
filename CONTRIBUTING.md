# PitchGuard — Contributing Guide

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, paper-ready code |
| `develop` | Integration branch |
| `phase/1-data-collection` | Phase 1 work |
| `phase/2-feature-engineering` | Phase 2 work |
| `phase/3-model-training` | Phase 3 work |
| `phase/4-dashboard` | Phase 4 work |

## Workflow

1. Branch from `develop`, not `main`
2. PR title: `[Phase N] Short description`
3. All PRs require passing CI (tests + lint)
4. Squash-merge to `develop`; merge `develop` → `main` at phase milestones

## Code Style

- **Black** for formatting (`black src/ tests/`)
- **Ruff** for linting (`ruff check src/ tests/`)
- Type hints on all public functions
- Docstrings on all modules and public functions

## Data

- Never commit raw scraped data (`data/raw/` is gitignored)
- The surface mapping CSV (`data/surface_mapping/stadium_surfaces.csv`) is committed and manually maintained
- Processed features go in `data/processed/` (gitignored for large files)

## Notebooks

- Use `notebooks/` for EDA only — no production logic
- Clear output before committing
