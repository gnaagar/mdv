---
title: "Orbit: Product Launch"
subtitle: "A faster way to turn ideas into shipped work"
author: "The Orbit Team"
date: 2026-10-08
---

## Meet Orbit

### From idea to momentum

One focused workspace for planning, building, and sharing your best work.

<!-- speaker -->
Welcome everyone. Today we are introducing Orbit — a modern approach to collaborative planning and shipping.

<!-- slide-sep -->

## Everyday Markdown

Write naturally with **bold emphasis**, *italics*, `inline code`, and [useful links](https://example.com).

Highlight critical details using accent colors: <!--blue-->**informative notes**<!--/blue-->, <!--green-->*verified results*<!--/green-->, <!--yellow-->`warning flags`<!--/yellow-->, or <!--red-->**urgent blockers**<!--/red-->.

<!--pink-->Variety<!--/pink--> of colors are <!--purple--> available<!--/purple-->.

### A lower-level heading

Markdown is still the primary authoring language; slides only add document metadata, separators, and column directives.

<!-- slide-sep -->

## Lists and tasks

<!-- col-start 1:1:1 none -->

### What we need

- A clear problem statement
- A small, testable first release
  - One owner
  - One measurable outcome

<!-- col-sep -->

### What to do

1. Draft the proposal
2. Review it together
3. Ship the decision

<!-- col-sep -->

### Where we are

- [x] <!--green-->Gather feedback (completed)<!--/green-->
- [ ] <!--yellow-->Publish the plan (in review)<!--/yellow-->
- [ ] <!--red-->Security sign-off (pending blocker)<!--/red-->

<!-- col-end -->

<!-- slide-sep -->

## A point of view

> Use blockquotes for principles, evidence, or a memorable line.

<!-- quote: blue -->
> <!--blue-->**Perspective**: Great presentations make **one idea** easy to carry forward.<!--/blue-->

<!-- quote: green -->
> <!--green-->**Evidence**: Small, frequent releases keep teams focused on real outcomes.<!--/green-->

<!-- quote: yellow -->
> <!--yellow-->**Guideline**: Keep slides focused; avoid clutter and preserve strong contrast.<!--/yellow-->

<!-- quote: pink -->
> <!--pink-->**Highlight**: Use accent colors intentionally to draw eyes to key metrics and takeaways.<!--/pink-->

<!-- quote: purple -->
> <!--purple-->**Summary**: Consistent styling builds rhythm across complex slide decks.<!--/purple-->

<!-- slide-sep -->

## Code is first-class

<!-- col-start 1:1 none:none -->

```python
# Compute readiness score from signals
def readiness_score(signals: dict) -> float:
    weights = {
        "tests_pass": 0.40,
        "review_approved": 0.35,
        "staging_green": 0.25,
    }
    return sum(
        weights.get(k, 0) * v
        for k, v in signals.items()
    )

def launch(signals: dict) -> str:
    score = readiness_score(signals)
    if score >= 0.9:
        return "🚀 ship it"
    return f"⏳ keep learning ({score:.0%})"
```

<!-- col-sep -->

```python
# Run the launch check
signals = {
    "tests_pass": 1.0,
    "review_approved": 1.0,
    "staging_green": 0.5,
}

result = launch(signals)
print(result)
# ⏳ keep learning (81%)

# Bump staging and retry
signals["staging_green"] = 1.0
print(launch(signals))
# 🚀 ship it
```

<!-- col-end -->

<!-- slide-sep -->

## Separators in code blocks

Slide separators inside code blocks or backticks are safely ignored and never split slides:

```markdown
## First Slide

Slide content here.

<!-- slide-sep -->

## Second Slide

Next slide content.
```

The `<!-- slide-sep -->` above is preserved verbatim inside the fenced code block.

<!-- slide-sep -->

## Data and math

| Signal | Target | This week |
| :--- | ---: | ---: |
| Activation | 60% | 64% |
| Weekly retention | 45% | 47% |

The familiar relationship: $a^2 + b^2 = c^2$.

$$
a^2 + b^2 = c^2
$$

<!-- slide-sep -->

## A Mermaid diagram

```mermaid
flowchart TD
    Idea[Idea] --> Plan[Plan]
    Plan --> Build[Build]
    Build --> Learn[Learn]
    Learn --> Idea
```

Mermaid blocks work just like they do in regular mdv documents.

<!-- slide-sep -->

## Another diagram

<!-- col-start 1:1 none -->

```mermaid
flowchart TD
    A{"`Is the sample process at its midpoint stage?`"} -- Yes --> B(Review the placeholder example item if you have the opportunity. Generic content for demonstration.)
    A -- No --> C(No further action is required at this stage)
```

<!-- col-sep -->

### The process

- A simple process, but a great example
- May lead to no action

```mermaid
flowchart LR
C["`A *text* **that** needs to be wrapped to another line`"]
```


<!-- col-end -->

<!-- slide-sep -->

## Built for flow

<!-- col-start 1:1 blue:green -->

### Plan

- Shape the outcome
- Keep context together
- Make the next step obvious

<!-- col-sep -->

### Ship

- Move from draft to delivery
- Share progress clearly
- <!--green-->**Learn from every release**<!--/green-->

<!-- col-end -->

<!-- quote: blue -->
> "Simplicity is prerequisite for reliability." — Edsger W. Dijkstra

<!-- speaker -->
- Emphasize that planning and shipping happen in the same unified workflow.
- Transition to the next slide demonstrating multi-column Markdown.

<!-- slide-sep -->

## Markdown in two columns

<!-- col-start 1:1 pink:purple -->

### A quote

> This is a **default** blockquote — it adapts to whatever background it sits on, appearing slightly darker.

<!-- quote: blue -->
> Columns can hold the same Markdown blocks as a full-width slide.

Use **emphasis**, `inline code`, and ordinary paragraphs without a special syntax.

<!-- col-sep -->

### A compact table

| Choice | Result |
| --- | --- |
| Small step | Fast learning |
| Big bet | Bigger risk |

<!-- col-end -->

<!-- slide-sep -->

## Table as column card

When a column contains **only** a table, it fills the card completely — no padding, borders merge.

<!-- col-start 1:1 blue:green -->

| Signal | Target | This week |
| :--- | ---: | ---: |
| Activation | 60 % | 64 % |
| Retention | 45 % | 47 % |
| NPS | 50 | 54 |

<!-- col-sep -->

### Notes

The right column has normal content — the flush-fill only applies when the table is the **sole** element in the card.

<!-- col-end -->

<!-- slide-sep -->

## Markdown in three columns

<!-- col-start 1:1:1 blue:yellow:green -->

### Plan

1. Name the outcome
2. Set a boundary

<!-- col-sep -->

### Build

```text
make it useful
```

<!--yellow-->
*Iterate quickly in small batches.*
<!--/yellow-->

<!-- col-sep -->

### Learn

- Measure the result
- Adjust the next step
- <!--green-->**Ship with confidence**<!--/green-->

<!-- col-end -->

<!-- slide-sep -->

## A two-row, three-column grid

<!-- col-start 1:1:1 -->

### Discover

Listen for the sharpest customer need.

<!-- col-sep -->

### Define

Write one measurable outcome.

<!-- col-sep -->

### Decide

Choose the smallest useful step.

<!-- col-end -->

<!-- col-start 1:1:1 -->

### Build

Keep the implementation focused.

<!-- col-sep -->

### Measure

Watch the signal that matters.

<!-- col-sep -->

### Learn

Use the result to guide the next cycle.

<!-- col-end -->

<!-- slide-sep -->

## A mixed row layout

<!-- col-start 1:1:1 red:yellow:green -->

### Blocked

<!--red-->
**High latency** on legacy database queries.
<!--/red-->

<!-- col-sep -->

### In progress

<!--yellow-->
Migrating cache tier to new cluster.
<!--/yellow-->

<!-- col-sep -->

### Resolved

<!--green-->
**Zero errors** recorded over the last 24 hours.
<!--/green-->

<!-- col-end -->

<!-- col-start 1:1 blue:blue -->

### Detail

Two larger areas work well for comparison.

<!-- col-sep -->

### Decision

Use the second row for the final trade-off.

<!-- col-end -->

<!-- col-start 1 green -->

### Conclusion

<!-- quote: green -->
> **Orbit simplifies complex flows**: Plan, collaborate, and ship safely.

<!-- col-end -->

<!-- slide-sep -->

## Blockquote styles

<!-- quote: blue -->
> **Blue**: Use blockquotes for principles, evidence, or a memorable line. The shadow gives them presence on a slide.

<!-- quote: green -->
> **Green**: Verified result or a positive finding worth highlighting.

<!-- quote: yellow -->
> **Yellow**: A caution or guideline the audience should carry forward.

<!-- quote: red -->
> **Red**: An urgent blocker or critical constraint — hard to miss.

<!-- slide-sep -->

## Table colour matching

When a column's only content is a table, borders and headers adopt the column palette.

<!-- col-start 1:1 blue:green -->

| Signal | This week |
| :--- | ---: |
| Activation | 64 % |
| Retention | 47 % |
| NPS | 54 |

<!-- col-sep -->

| Signal | This week |
| :--- | ---: |
| Build time | 42 s |
| Test pass | 98 % |
| Deploy freq | 3 / day |

<!-- col-end -->

<!-- slide-sep -->

## Invisible multi-column

<!-- col-start 1:1 none:none -->

### Left area

Columns divide the slide without any visible box or background. Content sits in its natural position with only the flex spacing between columns.

- Point one
- Point two
- Point three

<!-- col-sep -->

### Right area

The `none` colour removes border, background, and border-radius, making the split entirely invisible.

<!-- quote: blue -->
> Useful when you want layout control without the card look.

<!-- col-end -->

<!-- slide-sep -->

## Mixed: card + invisible

<!-- col-start 1:2 blue:none -->

### Highlight

<!-- quote: blue -->
> The left column can be a coloured card while the right is open.

<!-- col-sep -->

### Detail

Use `none` on just one side to anchor a card on the left or right while giving the remaining content room to breathe without boxing it in.

- No border
- No background
- Full padding preserved

<!-- col-end -->

<!-- slide-sep -->

## The result

Less coordination. More creation.

<!--green-->
**Orbit is available today.**
<!--/green-->

<!-- speaker -->
Thank the team and open the floor for Q&A.
