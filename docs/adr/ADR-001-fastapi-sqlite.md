# ADR-001: FastAPI + SQLite Local-First Backend

**Status:** Accepted  
**Date:** 2026-06-17

## Context

MVP requires local execution, minimal infrastructure, schema-first API contracts.

## Decision

- **FastAPI** for HTTP layer with auto OpenAPI
- **SQLite** for job metadata via SQLAlchemy (Postgres-swappable later)

## Consequences

- Single-host deployment for pilot
- SQLAlchemy abstraction enables future Postgres migration without API changes
