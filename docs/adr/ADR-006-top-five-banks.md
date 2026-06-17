# ADR-006: Top-5 Bank Statement Scope

**Status:** Accepted  
**Date:** 2026-06-17

## Context

Generic bank statement parsing is unbounded complexity.

## Decision

MVP supports SBI, HDFC, ICICI, Axis, Kotak only. Unsupported → Inconclusive.

## Consequences

- Bank-specific template strategies under `backend/engines/analyzer/statement/`
- Harness corpus organized by bank subfolder
