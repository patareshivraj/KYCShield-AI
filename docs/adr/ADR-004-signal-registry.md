# ADR-004: Plugin Signal Registry

**Status:** Accepted  
**Date:** 2026-06-17

## Context

Forensic capabilities must extend without modifying analyzer core.

## Decision

Signal plugins implement `SignalPlugin` protocol; register at startup. Document analyzers compose pipelines from registry.

## Consequences

- New signals (S02, P1) added as isolated modules under `backend/signals/`
