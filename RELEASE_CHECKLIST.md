# Open Source Release Checklist

> **Status**: All coupling points fixed, thesis fully pluggable.
> Last updated after configurability audit (Feb 2026).

---

## Step 1: Backup Private Files

Before touching git, stash your private config somewhere safe:

```bash
cd <your-radar-directory>

# Create backup of private files
mkdir ..\radar_private_backup
copy config\thesis.yaml ..\radar_private_backup\
copy .env ..\radar_private_backup\
xcopy data ..\radar_private_backup\data\ /E /I
xcopy scripts\one_off ..\radar_private_backup\scripts_one_off\ /E /I
xcopy outputs ..\radar_private_backup\outputs\ /E /I
```

## Step 2: Fresh Git Repository (REQUIRED)

Your existing `.git/` history contains `radar.db`, `thesis.yaml`, LinkedIn sessions,
and scripts with PE firm names (kester, inflexion, synova). These are **recoverable
from git log** even after deletion. You must start with a clean history.

```bash
# Delete old git history
rd /s /q .git

# Initialise clean repo
git init
git add .
```

## Step 3: Verify Nothing Sensitive Is Staged

```bash
# Should return NOTHING:
git diff --cached --name-only | findstr /i "thesis.yaml radar.db .env storage_state kester inflexion synova run_remote latest_briefing"

# Should return NOTHING:
git diff --cached --name-only | findstr /i "scripts\one_off scripts\debug scripts\seeding scripts\validation scripts\migrations"

# Should return NOTHING:
git diff --cached --name-only | findstr /i "\.db$ outputs\"

# Should see these PRESENT:
git diff --cached --name-only | findstr "thesis.example.yaml"
git diff --cached --name-only | findstr ".env.example"
git diff --cached --name-only | findstr ".gitkeep"
```

## Step 4: Content Audit Checklist

### Secrets & Credentials
- [ ] `.env` NOT staged (`.env.example` IS staged)
- [ ] `config/thesis.yaml` NOT staged (`thesis.example.yaml` IS staged)
- [ ] No API keys in source: `git diff --cached -S "sk-" --name-only` returns nothing
- [ ] `run_remote_server.bat` NOT staged (hardcoded admin/radar creds)

### Database & Data
- [ ] `data/radar.db` NOT staged
- [ ] `data/linkedin_session/` NOT staged
- [ ] `data/.gitkeep` IS staged (preserves directory structure)
- [ ] `outputs/.gitkeep` IS staged
- [ ] `latest_briefing.md` NOT staged

### Proprietary Scripts
- [ ] `scripts/one_off/` NOT staged (kester_discovery.py, batch_enrich_inflexion.py, etc.)
- [ ] `scripts/debug/` NOT staged
- [ ] `scripts/seeding/` NOT staged
- [ ] `scripts/validation/` NOT staged
- [ ] `scripts/migrations/` NOT staged
- [ ] `scripts/canonical/` IS staged
- [ ] `scripts/README.md` IS staged

### Frontend
- [ ] `src/web/ui/dist/` NOT staged
- [ ] `src/web/state.json` NOT staged

### Thesis Decoupling (VERIFIED by tests)
- [ ] `MoatType` enum does NOT exist in `src/core/models.py`
- [ ] `CompanyModel.moat_type` is `String(100)`, not `SQLEnum`
- [ ] `SemanticEnrichmentResult` uses `pillar_scores: Dict`, no hardcoded fields
- [ ] `scoring_impact_analyzer.py` reads from `thesis` singleton, not dead class attrs
- [ ] `MoatBreakdown.jsx` reads pillar keys from data dynamically
- [ ] `Methodology.jsx` fetches from `/config/thesis` API endpoint
- [ ] All 13 configurability tests pass: `pytest tests/unit/test_thesis_configurability.py -v`

## Step 5: Final Eyeball

```bash
git diff --cached --stat
```

**Should see:**
- `src/**/*.py`, `src/**/*.jsx` — infrastructure code
- `config/thesis.example.yaml` — generic 5-pillar example
- `.env.example` — template with blank API keys
- `data/.gitkeep`, `outputs/.gitkeep` — directory placeholders
- `docs/`, `tests/` — documentation and test suites
- `scripts/canonical/`, `scripts/README.md`
- `LICENSE`, `NOTICE`, `CONTRIBUTING.md`, `README.md`
- `pyproject.toml`, `docker-compose.yml`, `alembic.ini`
- `.gitignore`, `AGENTS.md`, `DEVELOPMENT.md`
- `RELEASE_CHECKLIST.md` (this file)

**Should NOT see:**
- `config/thesis.yaml`, `.env`, `*.db`
- `data/*` (except `.gitkeep`), `outputs/*` (except `.gitkeep`)
- `scripts/one_off/*`, `scripts/debug/*`, `scripts/seeding/*`
- `run_remote_server.bat`, `latest_briefing.md`
- `storage_state.json`, `src/web/state.json`

## Step 6: Push to GitHub as `open-radar`

```bash
git commit -m "Initial open-source release — Apache 2.0

Thesis-configurable PE deal sourcing platform.
All scoring, filtering, and LLM analysis driven by config/thesis.yaml.
See config/thesis.example.yaml for a working 5-pillar template."

git remote add origin https://github.com/YOUR_USERNAME/open-radar.git
git branch -M main
git push -u origin main
```

## Step 7: Set Up Private Working Copy

After the public repo is live, set up your working copy with private config:

```bash
# Clone fresh
git clone https://github.com/YOUR_USERNAME/open-radar.git radar-private
cd radar-private

# Restore private files from backup
copy ..\radar_private_backup\thesis.yaml config\thesis.yaml
copy ..\radar_private_backup\.env .env

# Optionally restore database (or bootstrap fresh)
copy ..\radar_private_backup\data\radar.db data\radar.db

# Optionally restore one-off scripts
xcopy ..\radar_private_backup\scripts_one_off scripts\one_off\ /E /I

# Verify private files are gitignored
git status
# Should show: nothing to commit, working tree clean
```

To pull framework updates from upstream:
```bash
git pull origin main
# Your private files stay untouched (gitignored)
```

---

## What's Public vs. Private

| Public (committed) | Private (gitignored) |
|---|---|
| All `src/` code | `config/thesis.yaml` (your weights & prompts) |
| `config/thesis.example.yaml` (5-pillar template) | PostgreSQL data (your company universe) |
| `.env.example` (blank template) | `.env` (your API keys) |
| `scripts/canonical/` | `scripts/one_off/` (PE firm research) |
| Tests (13 configurability + existing suites) | `scripts/debug/`, `scripts/seeding/` |
| Docs, web app source, Docker config | `outputs/` (generated reports) |
| `LICENSE` (Apache 2.0) | LinkedIn session data |
| `data/.gitkeep`, `outputs/.gitkeep` | Actual data in those directories |
