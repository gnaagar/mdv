# `md-slides` Specification (v0.1 Draft)

**Recommended File Extension:** `.slides.md`

**Purpose:** A concise syntax specification for authoring presentations in plain Markdown text. Content remains human-readable as a standard text document while expressing structural presentation metadata and layouts.

---

## 1. Document Structure

An `md-slides` document consists of:

1. **Header / Metadata:** Standard YAML Frontmatter at the beginning of the file.
2. **Preamble (Optional):** Free markdown content before the first `<!-- slide -->` directive. This content is rendered in standard document viewers but ignored in the presentation viewer.
3. **Slides:** Each slide begins with a `<!-- slide -->` directive followed by a required `## Slide Title`. Slide content continues until the next `<!-- slide -->` directive or the end of the document.

---

## 2. Metadata (YAML Frontmatter)

The document MUST start with a YAML frontmatter block enclosed by triple-dashed lines (`---`).

### Supported Fields

| Field | Type | Description |
| --- | --- | --- |
| `title` | String | Presentation main title |
| `subtitle` | String | Subtitle or brief overview |
| `author` | String | Presenter or author name |
| `date` | String / Date | Presentation date |
| `footer` | String | Optional custom footer text on the bottom-left of each slide (default: none) |

### Syntax Example

```yaml
---
title: "Building Modern Systems"
subtitle: "An architectural overview for 2026"
author: "Alex Mercer"
date: 2026-10-08
footer: "Acme Corp • Confidential"
---
```

### Slide Footer & Page Numbers

* **Slide Numbers:** Positioned on the bottom-right of each slide (`1 / N`).
* **Custom Footer:** By default, no custom footer is rendered. When `footer` is specified in frontmatter, it is displayed on the bottom-left in the exact same font, size, and muted color as the slide numbers.

---

## 3. Slide Declaration & Vertical Centering

Each slide begins with a `<!-- slide -->` directive on its own line:

```markdown
<!-- slide -->
```

### Vertical Centering (Default)

By default, slide content is vertically centered beneath its fixed top header banner. This standard presentation layout ensures slides look balanced regardless of screen aspect ratio:

* **Default Center Alignment:** `<!-- slide -->` (or explicit `<!-- slide align:center -->`)
  The header title remains pinned at the top, and all slide content (columns, flow cards, text, images) is centered vertically in the space below.
* **Top Alignment:** `<!-- slide align:top -->`
  Disables vertical centering for content-dense slides, aligning body content to the top.

### Slide Preamble

Any markdown text placed between the YAML frontmatter and the first `<!-- slide -->` directive is treated as a preamble. It renders normally in standard markdown viewers (e.g. GitHub or `mdv` workspace viewer) and is automatically skipped in slide mode.

### Code Blocks

`<!-- slide -->` directives placed inside fenced code blocks (```` ``` ```` or `~~~`) or inline backticks are preserved verbatim as code without splitting slides.

### Address Bar Navigation

You can link or jump directly to any slide by adding `#<slide_number>` to the URL (for example, `http://localhost:8000/#3` for Slide 3).

### Syntax Example

```markdown
---
title: "System Architecture"
---

# Document Preamble
Notes visible in regular document view, ignored in slides.

<!-- slide -->

## Introduction

This slide body is vertically centered by default.

<!-- slide align:top -->

## Detailed Specifications

This slide body is top-aligned to accommodate longer content.
```

---

## 4. Multi-Column Layouts (`<!-- col -->`)

Columns are declared inside a slide using paired HTML comments following the `col` and `/col` convention:

### Directive Syntax

1. **Start Column Block:** `<!-- col <ratio> [colors] -->`
   * `<ratio>` defines column width proportions as colon-separated integers or floats (e.g., `1:1`, `1:2`, `2:1:5`).
   * The number of values in `<ratio>` defines the total column count.
   * Optional `[colors]` assigns background tint colors to columns (e.g., `yellow:blue` or `blue`).
2. **Column Separator:** `<!-- col-sep [color] -->`
   * Marks the boundary between adjacent columns.
   * Can optionally override the column color (e.g. `<!-- col-sep green -->`).
3. **End Column Block:** `<!-- /col -->`
   * Closes the column layout and returns to full-width rendering.

### In-Column Accent Color

You can also set the color of a column using `<!-- col-color: <color> -->` within that column:

```markdown
<!-- col 1:1 -->
<!-- col-color: yellow -->
### Left Column
<!-- col-sep -->
<!-- col-color: green -->
### Right Column
<!-- /col -->
```

---

## 5. Flow Pipelines (`<!-- flow -->`)

Flow blocks render sequences of connected cards with directional SVG arrows, ideal for multi-step pipelines, architectures, and lifecycles.

### 5.1 Horizontal Flow Pipelines

Render a horizontal flex row with right-pointing arrows between cards:

```markdown
<!-- flow blue:green:purple -->
1. **Discover**
   - User interviews & signals
2. **Build**
   - Sprint execution & CI
3. **Ship**
   - Canary progressive rollout
<!-- /flow -->
```

* **Number Badges:** When an ordered list (`1.`, `2.`, `3.`) is used, circular pill badges are rendered.
* **Unordered Lists:** Use `-` or `*` for cards without number badges.
* **Closing Tag:** Closes with `<!-- /flow -->`.

### 5.2 Vertical Flow

Render a vertical sequence of cards connected by downward-pointing arrows:

```markdown
<!-- flow vertical blue:green:yellow -->
1. **Frontend Experience**
   Next.js edge runtime
2. **Core Engine & API**
   FastAPI async workers
3. **Storage & Analytics**
   Distributed PostgreSQL
<!-- /flow -->
```

### 5.3 Explicit Step Separators (`<!-- flow-sep -->`)

For arbitrary multi-paragraph or complex Markdown blocks within flow steps:

```markdown
<!-- flow blue:green -->
### Ingestion
Raw event streams are buffered in memory.
<!-- flow-sep -->
### Processing
Async workers transform and batch payloads.
<!-- /flow -->
```

---

## 6. Centered Content (`<!-- center -->`)

To center specific content blocks (such as logos, hero statements, or diagrams) within a slide, use `center` and `/center`:

### Directive Syntax

* **Horizontal Centering (Default):** `<!-- center -->` or `<!-- center horizontal -->`
  Centers text and auto-centers block elements horizontally.
* **Vertical Centering:** `<!-- center vertical -->`
  Expands to fill available height and vertically centers content while preserving text alignment.
* **Both Dimensions:** `<!-- center both -->`
  Centers content both horizontally and vertically.
* **Closing Tag:** Closes with `<!-- /center -->`.

### Syntax Example

```markdown
<!-- center -->
![Architecture Diagram](/static/diagram.svg)
<!-- /center -->

<!-- center both -->
> ### "The best way to predict the future is to invent it."
> — Alan Kay
<!-- /center -->
```

---

## 7. Accent Colors

All accent styling uses HTML comments so that documents remain 100% valid, portable plain Markdown.

Supported accent colors: `yellow`, `red`, `green`, `blue`, `pink`, `purple`, `grey` / `gray` (and `none` for unstyled).

### 7.1 Text Accent Colors

Color individual words, lines, or blocks of Markdown content using the canonical format:

* **Syntax:** `<!--<color>-->content<!--/<color>-->`
* **Examples:**
  - `<!--red-->urgent blocker<!--/red-->`
  - `<!--green-->**verified result**<!--/green-->`
  - `<!--blue-->informative text<!--/blue-->`

### 7.2 Blockquote Accent Colors

Apply accent border-left, tinted background, and matching accent text color to blockquotes:

* **Before blockquote:** `<!-- quote: green -->`
* **Inside first line:** `> <!-- quote: green --> Safe and reversible.`
* **Default Accent Text:** Text inside the blockquote is automatically styled in the accent color by default, keeping the Markdown clean without requiring nested `<!--color-->` tags.
* **Neutral Text Override:** To keep default body text color while styling the border and background, pass `none` as the text option: `<!-- quote: green none -->`.

---

## 8. Speaker Notes (`<!-- speaker -->`)

Any Markdown content below `<!-- speaker -->` until the next `<!-- slide -->` directive or the end of document is treated as speaker notes:

```markdown
<!-- slide -->

## Production Readiness

All verification checks have passed.

<!-- speaker -->
> **SPEAKER NOTES**
>
> - Mention latency graphs
> - Thank the deployment and QA teams
```

* **In normal Markdown viewers:** The `<!-- speaker -->` comment is hidden and the notes remain visible as ordinary text.
* **In slide presentation:** Speaker notes are excluded from the presentation screen.

---

## 9. Complete Example Document

```markdown
---
title: "Decentralized Storage Protocols"
subtitle: "Comparing modern network architectures"
author: "Engineering Team"
date: 2026-10-08
---

<!-- slide -->

## Overview

Welcome to the presentation. This slide body is vertically centered by default.

- Simple text formatting
- Code blocks and lists behave as usual

<!-- speaker -->
> **SPEAKER NOTES**
>
> Introduce the session goal and agenda briefly before diving into architecture.

<!-- slide -->

## Key Metrics & Architecture

<!-- col 1:2 -->

### Core Principles

- High availability
- Fault tolerance
- Encrypted channels

<!-- col-sep -->

### Performance

| Metric | Target | Actual |
| :--- | :--- | :--- |
| Latency | < 50ms | 32ms |
| Uptime | 99.9% | 99.95% |

<!-- /col -->

<!-- slide align:top -->

## Three-Column Summary

<!-- col 2:1:5 yellow:blue:green -->

### Left Column (Ratio 2)
Broader introductory notes or context.

<!-- col-sep -->

### Middle (Ratio 1)
Key takeaway or visual cue.

<!-- col-sep -->

### Right Column (Ratio 5)
Detailed analysis, code snippets, or extended discussion.

<!-- /col -->
```
