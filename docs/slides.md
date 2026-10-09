# `md-slides` Specification (v0.1 Draft)

**Recommended File Extension:** `.slides.md`

**Purpose:** A concise syntax specification for authoring presentations in plain Markdown text. Content remains human-readable as a standard text document while expressing structural presentation metadata and layouts.

---

## 1. Document Structure

An `md-slides` document consists of two main sections:

1. **Header / Metadata:** Standard YAML Frontmatter at the beginning of the file.
2. **Body:** Standard Markdown content partitioned into individual slides and columnar blocks.

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

### Syntax Example

```yaml
---
title: "Building Modern Systems"
subtitle: "An architectural overview for 2026"
author: "Alex Mercer"
date: 2026-10-08
---

```

---

## 3. Slide Separation

Slides are separated by a line containing **three or more hyphens (`---`)** on a standalone line.

* Trailing or leading whitespace on the separator line is ignored.
* Content before the first `---` separator (excluding frontmatter) belongs to Slide 1.

### Syntax Example

```markdown
# Slide 1 Title

Slide 1 content goes here.

---

# Slide 2 Title

Slide 2 content goes here.

```

---

## 4. Multi-Column Layouts

Columns are declared inside a slide using HTML comments. This ensures presentation layout instructions do not interfere with standard Markdown rendering in simple previewers.

### Directive Syntax

1. **Start Column Block:** `<!-- col-start <ratio> -->`
* `<ratio>` defines the column width proportions, expressed as colon-separated integers or floats (e.g., `1:1`, `2:1:5`, `1:2:1`).
* The number of values in the ratio defines the total number of columns expected.


2. **Column Separator:** `<!-- col-sep -->`
* Marks the boundary between adjacent columns.


3. **End Column Block:** `<!-- col-end -->`
* Closes the column layout section and returns to full-width rendering.



### Rules & Semantics

* Column directives MUST be placed on their own dedicated lines.
* Content inside columns supports standard Markdown syntax.
* Every `col-start` block MUST be matched with a corresponding `col-end`.
* The number of `col-sep` directives within a block MUST equal $N - 1$, where $N$ is the count of proportions in the `col-start` ratio.

---

## 5. Accent Colors (HTML Comments)

All accent styling uses HTML comments so that documents remain 100% valid, portable plain Markdown across any standard viewer.

Four standard accent colors are supported: `yellow`, `red`, `green`, and `blue`.

### 5.1 Column Box Accent Colors
Accent colors apply a matching background tint and colored border to column cards.

* **Inside a column:** `<!-- col-color: <color> -->` (e.g. `<!-- col-color: yellow -->`, `<!-- col-green -->`, `<!-- accent: red -->`)
* **In block declaration:** `<!-- col-start 1:1 blue:green -->` or `<!-- col-start 1:1 yellow -->`
* **In separator:** `<!-- col-sep green -->`

### 5.2 Text Accent Colors
Color individual words, lines, or blocks of Markdown content:

* **Inline:** `<!-- color: red -->urgent<!-- /color -->` or `<!-- green -->success<!-- /green -->`
* **Block:**
  ```markdown
  <!-- color: blue -->
  ### Key takeaway
  - First point
  <!-- /color -->
  ```

### 5.3 Blockquote Accent Colors
Apply accent border-left and tinted background to blockquotes:

* **Before blockquote:** `<!-- quote: green -->`
* **Inside first line:** `> <!-- quote: green --> Safe and reversible.`

---

## 6. Speaker Notes

Any Markdown content below an HTML comment starting with `<!-- speaker -->` until the start of the next slide (`---`) or the end of the document is treated as speaker notes.

* **In normal Markdown viewers:** The `<!-- speaker -->` comment is hidden and the notes remain visible as ordinary text.
* **In the slide presentation:** Speaker notes are excluded from the visible presentation slide.

```markdown
## Production Readiness

All verification checks have passed.

<!-- speaker -->
- Mention latency graphs
- Thank the deployment and QA teams
```

---

## 7. Complete Example Document

```markdown
---
title: "Decentralized Storage Protocols"
subtitle: "Comparing modern network architectures"
author: "Engineering Team"
date: 2026-10-08
---

# Overview

Welcome to the presentation. This slide uses standard full-width Markdown.

- Simple text formatting
- Code blocks and lists behave as usual

---

# Key Metrics & Architecture

<!-- col-start 1:2 -->

## Core Principles

- High availability
- Fault tolerance
- Encrypted channels

<!-- col-sep -->

## Performance

| Metric | Target | Actual |
| :--- | :--- | :--- |
| Latency | < 50ms | 32ms |
| Uptime | 99.9% | 99.95% |

<!-- col-end -->

---

# Three-Column Summary

<!-- col-start 2:1:5 -->

### Left Column (Ratio 2)
Broader introductory notes or context.

<!-- col-sep -->

### Middle (Ratio 1)
Key takeaway or visual cue.

<!-- col-sep -->

### Right Column (Ratio 5)
Detailed analysis, code snippets, or extended discussion.

<!-- col-end -->

```
