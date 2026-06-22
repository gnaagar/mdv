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

---

## 9. Massive Sales Dataset (10 Columns x 20 Rows)
A wide, dense table containing transaction logs to test high-density responsive grids, scroll shadows, and full-screen exploration zoom/pan widgets.

| TX ID | Region | Product Class | Unit Price | Units Sold | Gross Rev | Tax Rate | Net Rev | Shipping | Delivery Status |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| TX-801 | North America | Electronics | $399.99 | 150 | $59,998.50 | 8.5% | $54,898.63 | Express | Delivered |
| TX-802 | Europe | Home Appliance | $189.50 | 320 | $60,640.00 | 20.0% | $48,512.00 | Standard | In Transit |
| TX-803 | Asia-Pacific | Office Supplies | $12.75 | 1200 | $15,300.00 | 10.0% | $13,770.00 | Economy | Delivered |
| TX-804 | South America | Automotive | $85.00 | 450 | $38,250.00 | 12.0% | $33,660.00 | Standard | Processing |
| TX-805 | Middle East | Industrial | $1250.00 | 30 | $37,500.00 | 5.0% | $35,625.00 | Express | Out for Delivery |
| TX-806 | Africa | Telecommunications | $45.00 | 950 | $42,750.00 | 15.0% | $36,337.50 | Standard | Delivered |
| TX-807 | North America | Apparel & Shoes | $65.00 | 1100 | $71,500.00 | 8.5% | $65,422.50 | Priority | Delivered |
| TX-808 | Europe | Food & Beverage | $4.25 | 8500 | $36,125.00 | 7.0% | $33,596.25 | Economy | Delivered |
| TX-809 | Asia-Pacific | Sports & Outdoors | $120.00 | 250 | $30,000.00 | 10.0% | $27,000.00 | Express | Processing |
| TX-810 | North America | Furniture & Decor | $450.00 | 80 | $36,000.00 | 6.0% | $33,840.00 | Standard | In Transit |
| TX-811 | Europe | Health & Beauty | $35.00 | 1450 | $50,750.00 | 18.0% | $41,615.00 | Standard | Delivered |
| TX-812 | Asia-Pacific | Video Games | $59.99 | 980 | $58,790.20 | 8.0% | $54,086.98 | Priority | Delivered |
| TX-813 | South America | Toys & Hobbies | $24.99 | 1800 | $44,982.00 | 12.0% | $39,584.16 | Economy | In Transit |
| TX-814 | Middle East | Construction | $320.00 | 140 | $44,800.00 | 5.0% | $42,560.00 | Express | Delivered |
| TX-815 | Africa | Agriculture | $15.50 | 3100 | $48,050.00 | 10.0% | $43,245.00 | Standard | Processing |
| TX-816 | North America | Musical Instruments | $899.00 | 65 | $58,435.00 | 8.5% | $53,468.03 | Priority | Out for Delivery |
| TX-817 | Europe | Books & Media | $14.95 | 4200 | $62,790.00 | 5.0% | $59,650.50 | Economy | Delivered |
| TX-818 | Asia-Pacific | Pet Supplies | $28.50 | 1650 | $47,025.00 | 10.0% | $42,322.50 | Standard | Delivered |
| TX-819 | South America | Health & Fitness | $110.00 | 480 | $52,800.00 | 15.0% | $44,880.00 | Priority | Delivered |
| TX-820 | North America | Hardware Tools | $75.00 | 680 | $51,000.00 | 8.5% | $46,665.00 | Standard | In Transit |


