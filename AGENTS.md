# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SyncObsidian is a self-hosted Obsidian synchronization service. It consists of two modules:
- **backend/** — FastAPI (Python) REST API with async SQLite, serving note and attachment sync
- **obsidian-plugin/** — TypeScript Obsidian plugin that communicates with the backend

Primary language for documentation and commit messages is French.

Read @README.md for more information.

## Architecture

### Backend

Layered architecture: **Routers → Services → Core**

- `app/routers/auth.py` — `/auth/*` endpoints (register, login, me)
- `app/routers/sync.py` — `/sync/*` endpoints (push, pull, compare, attachments, notes list)
- `app/services/` — Business logic split by domain:
  - `notes_sync.py` — Note push/pull, conflict handling, deletion tracking
  - `attachments_sync.py` — Attachment push/pull (base64, 25MB limit)
  - `compare_sync.py` — Delta detection and conflict identification
  - `sync_utils.py` — Shared helpers (SHA256 hashing, query utilities)
- `app/core/` — Infrastructure: `database.py` (async SQLAlchemy + SQLite), `security.py` (JWT + bcrypt), `storage.py` (file ops), `config.py` (env-based settings)
- `app/models.py` — ORM models: User, Note, Attachment (notes/attachments scoped per user, unique path per user)
- `app/schemas.py` — Pydantic request/response schemas

### Plugin

```
SyncObsidianPlugin (main.ts)  — Entry point, ribbon/commands/auto-sync
├─ SyncService (sync-service.ts)    — Orchestrates sync flow, conflict detection
├─ ApiClient (api-client.ts)        — HTTP client for backend API
├─ Settings (settings.ts)           — Settings tab UI
└─ ReportFormatter (report-formatter.ts) — Sync report display
```

Deletion tracking uses `knownFiles`/`knownAttachments` arrays persisted in plugin data. Mocks for `obsidian` module live in `src/__mocks__/obsidian.ts`.

### Data Flow

Client compares local state → sends metadata to `/sync` → server returns diff → client pushes/pulls changed notes and attachments individually → server stores content with SHA256 hashes for change detection.

## Conventions

### Design and code quality

Follow `SOLID` principes as described in `Clean Code`. Avoid code duplication. Keep design simple, make pragmatic choices (tradeoffs between complexity VS maintanability)

### Commits

Before commiting, when necessary, remove element of backlog in @TODO.md.
Use Conventional Commits. Scopes: `api`, `plugin`, `api+plugin`. Types: `fix`, `feat`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`. Do not include `Co-Authored-By` in commit messages. Use the `/commit` skill (gitcp) when committing.

### Plugin Versioning

Versions follow `<major>.<minor>.<patch>`. Features and bug fixes increment `<minor>` only (e.g., 1.7.0 → 1.8.0). Only change `<major>` or `<patch>` if explicitly requested. **Always update `obsidian-plugin/manifest.json`** when implementing a feature or bug fix.

### Testing

- Add unit tests (and integration tests when needed) for every new feature or bug fix
- Use TDD (red/green/refactor) for bug fixes
- Do not modify existing tests to make them pass unless the expected behavior changed
- Run all tests in the affected module before committing

### Workflow

- Ask clarifying questions to reduce uncertainty
- For complex tasks: ask questions → produce spec + implementation plan → get approval before coding
- Always summarize the action plan and number of files to modify, then ask for approval. Analyze the impact of your implementation proposal regarding :
  - code quality (duplication, maintenability, complexity) and the tradeoffs you made
  - librairies (new, updated, removed)

## Test Configuration

- **Backend**: pytest with `asyncio_mode = auto`, test files in `backend/tests/` and `backend/tests/unit/`
- **Plugin**: Jest with ts-jest, mock mappings in `jest.config.js`, tests in `src/__tests__/`

## Specs & Backlog

Detailed technical specs live in `docs/` (attachments sync, rate limiting, refresh tokens, sync report, paginated notes endpoint). The backlog with priority matrix is in `TODO.md`.