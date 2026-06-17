# ADR-003: Dual PDF Strategy (PyMuPDF + pdfplumber)

**Status:** Accepted  
**Date:** 2026-06-17

## Context

PDFs require rasterization, structure forensics (S05), and table extraction (S12).

## Decision

- **PyMuPDF:** normalization, rasterization, object-level forensics
- **pdfplumber:** bank statement table parsing

## Consequences

- Two PDF dependencies; clear stage ownership per library
