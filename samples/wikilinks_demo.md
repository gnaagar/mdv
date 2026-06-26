# Wikilinks Resolution Showcase

Welcome to the Wikilinks Demo! This document showcases the **nearest suffix resolution** feature.

## 1. Simple Unique Suffixes
- Link to `diagrams.md`: [[diagrams]]
- Link to `projects/mdv/features/modal.md` using just the filename: [[modal]]

## 2. Partial Suffix Path Resolution
- Link to `projects/mdv/architecture.md` using a longer suffix: [[mdv/architecture]]

## 3. Custom Labels (Piped Syntax)
- Link to standard pages with custom text: [[acme|Read about ACME Corp]]

## 4. Conflict Resolution (Ambiguous Suffixes)
We have two files named `setup.md` in the workspace:
- `samples/tutorials/javascript/setup.md`
- `samples/projects/mdv/setup.md`

If we write a link using only `[[setup]]`, it matches multiple files and renders as a **broken link**:
- Ambiguous link: [[setup]]

However, if we provide a slightly longer nearest suffix, it resolves **uniquely**:
- Link to JavaScript Setup: [[javascript/setup]]
- Link to MDV Setup: [[mdv/setup]]
