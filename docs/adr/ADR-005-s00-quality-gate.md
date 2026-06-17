# ADR-005: S00 Quality Gate Before Forensics

**Status:** Accepted  
**Date:** 2026-06-17

## Context

Phone photos and WhatsApp forwards cause forensic false positives.

## Decision

S00 runs before OCR-dependent fraud signals. Quality fail → Inconclusive; warn → Tier C confidence cap.

## Consequences

- Quality failure never maps to Low risk band
- Additional pipeline stage and QualityProfile schema required
