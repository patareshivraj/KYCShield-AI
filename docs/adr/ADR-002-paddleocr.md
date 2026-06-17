# ADR-002: PaddleOCR for Indian Script OCR

**Status:** Accepted  
**Date:** 2026-06-17

## Context

KYC documents contain Devanagari and English. OCR errors mimic tampering flags.

## Decision

**PaddleOCR** as primary OCR engine. Tesseract optional English-only fallback.

## Consequences

- Larger dependency footprint; bundle models for offline install
- Better cross-document name matching for Hindi/English transliteration
