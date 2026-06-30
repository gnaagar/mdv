# Wikilinks and Heading Anchors Specification

This document provides a guide for writers to understand how wikilinks are resolved, how heading anchors are generated, and how to write links.

---

## 1. Wikilink Resolution: Nearest-First Strategy

When you write a wikilink like `[[setup]]` or `[[tutorials/setup]]`, the viewer automatically locates the target document in the workspace using a **Nearest-First** strategy relative to the document containing the link.

### LCA Distance Priority

The distance from the directory of the current file (`S`) to a candidate target file (`C`) is calculated using a tuple `(d_up, d_down)` representing the steps up to the Lowest Common Ancestor (LCA) directory and down to the candidate folder:

1. **Siblings** `(0, 0)`: Matches in the same directory as the current file.
2. **Children (BFS)** `(0, 1)`, `(0, 2)`, ...: Matches in direct subfolders, then nested sub-subfolders.
3. **Parents & Grandparents** `(1, 0)`, `(1, 1)`, ...: Matches in parent/grandparent directories and their other subtrees.

### Ambiguity / Collision Rule

* If **multiple files** match the suffix at the **same closest distance**, the resolution is considered ambiguous.
* In case of an ambiguous match, the link will not resolve and will be styled as a **broken link**.
* To fix this, provide a slightly longer suffix prefix. For example:
  * Instead of `[[setup]]` (which might match both `a/setup.md` and `b/setup.md` from the root), write `[[a/setup]]` or `[[b/setup]]` to resolve it uniquely.

---

## 2. Heading Anchor Generation (Slugification)

When headings are rendered into HTML, they are given unique `id` anchors so you can link to them. The anchor for a heading is generated using the following rules:

1. **Lowercase**: Converts the heading text to lowercase.
2. **Alphanumeric Filter**: Extracts only sequences of Unicode alphanumeric characters (punctuation and underscores `_` are stripped).
3. **Word Limit**: Limits the slug to the first **4 words** of the heading.
4. **Hyphen Join**: Joins the extracted words with a single hyphen `-`.
5. **Fallback**: If no valid alphanumeric characters exist in the heading, it defaults to `"heading"`.
6. **Duplication Resolution**: If multiple identical slugs exist on the same page, the parser appends `-1`, `-2`, etc., in the order of appearance.

### Example Anchor Mappings

| Raw Heading | Generated Anchor |
| :--- | :--- |
| `# 1. Getting Started Guide` | `getting-started-guide` |
| `## Raw - Heading without processing` | `raw-heading-without-processing` |
| `### Long Heading Containing Too Many Words For The Limit` | `long-heading-containing-too` (limited to 4 words) |
| `## !!!` | `heading` (fallback) |

---

## 3. Writing Anchor Links

You can link directly to a specific section/heading in a document using the `#` character.

### Raw Heading Match

You **do not** need to manually calculate the slugified anchor. You can write the raw heading text directly in the anchor portion of the link, and the engine will process it through the slugify algorithm automatically at render time:

* **Example Source**: `[[recipes/apple-pie#Ingredients List]]`
* **How it resolves**: The system finds the file `recipes/apple-pie.md` and automatically processes `#Ingredients List` into the lowercase, hyphenated `#ingredients-list` anchor.

Of course, if you already know the slugified anchor, you can also write it directly: `[[recipes/apple-pie#ingredients-list]]`. Both resolve to the same section.
