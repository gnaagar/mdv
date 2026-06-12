# Markdown Tables Test

This document contains various types of tables to test layout rendering, responsiveness, and overflow styling.

---

## 1. Standard Table
A clean, typical table with text alignment.

| Product ID | Description | Price | Status |
| :--- | :--- | :---: | :---: |
| APP-001 | Fresh red apples from local orchards | $2.99 | In Stock |
| BAN-002 | Organic Cavendish bananas | $1.49 | Out of Stock |
| ORG-003 | Sweet seedless Valencia oranges | $3.99 | In Stock |

---

## 2. Wide Table (Many Columns)
A table with many columns that should trigger horizontal overflow/scrolling.

| Rank | Name | Q1 | Q2 | Q3 | Q4 | YTD | Goal | Delta | Status | Notes |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | Alice Smith | 92% | 95% | 98% | 97% | 95.5% | 90% | +5.5% | Met | Excellent performance |
| 2 | Bob Jones | 85% | 88% | 84% | 90% | 86.8% | 90% | -3.2% | Pending | Needs minor improvement |
| 3 | Charlie Brown | 78% | 80% | 82% | 85% | 81.2% | 80% | +1.2% | Met | Consistently on track |
| 4 | Diana Prince | 99% | 98% | 100% | 99% | 99.0% | 90% | +9.0% | Met | Outstanding leadership |

---

## 3. Very Wide Columns
A table where cells contain long sentences or code snippets, causing individual columns to stretch.

| Key Feature | Detailed Explanation & Technical Description | Implementation Details & References |
| :--- | :--- | :--- |
| **Responsive Grid** | The grid system adjusts elements based on viewport size, prioritizing readability on smaller screens and high-density displays. | Implemented using standard CSS Grid layouts with fallback flexbox structures. |
| **Theme Customization** | Supports multiple themes (sans, sans-dark, serif, monospace) loaded dynamically via CSS variables and system preferences. | Powered by global theme stylesheets loaded on-demand in the document head. |

---

## 4. Single Column Table
A table with only one column.

| Checklist Item |
| :--- |
| [ ] Review and test responsive table overflow |
| [ ] Add subtle shadows to scrollable tables |
| [ ] Support clean typography inside tables |

---

## 5. Headerless / Empty Header Table
A table structure where the headers are empty or omitted.

| | | |
| --- | --- | --- |
| Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
| Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |

---

## 6. Irregular / Malformed Table
A table with mismatched column counts, missing cells, or incorrect cell alignment markers to test parser resilience and layout stability.

| Col A | Col B | Col C |
| --- | --- |
| Mismatched | rows |
| Missing | third | column | here |
| Extra | pipe | at the end | | |

---

## 7. Small Key-Value Table
A compact table typically used for metadata or basic settings.

| Setting | Value |
| :--- | :--- |
| Version | 1.4.2 |
| Environment | Production |

---

## 8. Small 3x2 Matrix (Feature checklist)
A small comparison or checklist table.

| Feature | Core | Lite |
| :--- | :---: | :---: |
| Autocomplete | ✓ | ✗ |
| Search | ✓ | ✓ |

