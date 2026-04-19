"""
Worklog markdown parser.

Understands the following structure:

    # Title (anything)

    ## Week YYYY-Www          ← week section (parsed)
    ### YYYY-MM-DD            ← day section (parsed)
    - [x] task text -- t:1h30m
      - [x] subtask -- t:45m  (arbitrary depth, time on leaves)

    ## Guidelines             ← ignored section
    ...

    ## Config                 ← config section
    | target hours | 6 |
    | baseline hours | 4 |
"""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

RE_WEEK       = re.compile(r"^##\s+Week\s+(\d{4}-W\d{2})\s*$")
RE_DAY        = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s*$")
RE_SECTION    = re.compile(r"^##\s+(.+)$")
RE_TASK       = re.compile(
    r"^-\s+\[(?P<state>[x /\-])\]\s+(?P<text>.+?)(?:\s+--\s+(?P<meta>.+))?$",
    re.IGNORECASE,
)
RE_DURATION   = re.compile(r"t:(?=\d)(?:(?P<hours>\d+)h)?(?:(?P<mins>\d+)m)?")
RE_CONFIG_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParseWarning:
    line_no: int
    message: str
    severity: str          # "error" | "warning"
    line: str = ""         # the offending source line (for display)


@dataclass
class Task:
    text: str
    done: bool             # [x]
    in_progress: bool      # [/]
    cancelled: bool        # [-]
    time_min: int          # own time; meaningful only on leaf nodes
    blocked: bool          # (blocked) annotation present
    raw_meta: str          # everything after --
    line_no: int = 0
    children: list["Task"] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def total_time_min(self) -> int:
        """Leaf: own time. Non-leaf: sum of children (own time ignored)."""
        if self.is_leaf:
            return self.time_min
        return sum(c.total_time_min for c in self.children)


@dataclass
class Day:
    date: date
    line_no: int = 0
    tasks: list[Task] = field(default_factory=list)

    @property
    def total_time_min(self) -> int:
        return sum(t.total_time_min for t in self.tasks)

    @property
    def done_count(self) -> int:
        return sum(1 for t in _iter_leaves(self.tasks) if t.done)

    @property
    def total_count(self) -> int:
        return sum(1 for _ in _iter_leaves(self.tasks))

    @property
    def blocked_tasks(self) -> list[Task]:
        return [t for t in _iter_leaves(self.tasks) if t.blocked]


@dataclass
class Week:
    iso_week: str            # e.g. "2026-W16"
    days: list[Day] = field(default_factory=list)

    @property
    def total_time_min(self) -> int:
        return sum(d.total_time_min for d in self.days)


@dataclass
class WorklogConfig:
    target_hours: float = 6.0
    baseline_hours: float = 0.0   # minimum recommended; 0 = not set


@dataclass
class Worklog:
    title: str
    weeks: list[Week]
    config: WorklogConfig
    warnings: list[ParseWarning] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_leaves(tasks: list[Task]):
    """Recursively yield leaf tasks (tasks with no children)."""
    for t in tasks:
        if t.is_leaf:
            yield t
        else:
            yield from _iter_leaves(t.children)


def _parse_duration(meta: str) -> tuple[int, bool]:
    """
    Return (total_minutes, matched).
    matched=False means t: was present but regex didn't recognise the format.
    """
    m = RE_DURATION.search(meta)
    if m:
        hours = int(m.group("hours") or 0)
        mins  = int(m.group("mins")  or 0)
        return hours * 60 + mins, True
    return 0, False


def _parse_task_line(
    raw: str, line_no: int
) -> tuple[Optional[Task], list[ParseWarning]]:
    """
    Parse a single task line (stripped of leading whitespace).
    Returns (Task | None, warnings).
    """
    warns: list[ParseWarning] = []
    m = RE_TASK.match(raw.strip())
    if not m:
        return None, warns

    state    = m.group("state").strip().lower()
    text     = m.group("text").strip()
    meta_raw = (m.group("meta") or "").strip()

    done        = state == "x"
    in_progress = state == "/"
    cancelled   = state == "-"
    blocked     = "blocked" in meta_raw.lower()

    time_min = 0
    if meta_raw:
        time_min, matched = _parse_duration(meta_raw)
        if not matched and "t:" in meta_raw.lower():
            warns.append(ParseWarning(
                line_no=line_no,
                message=(
                    f"Invalid duration format in metadata: '{meta_raw}'. "
                    f"Expected formats: t:30m  t:1h  t:1h30m"
                ),
                severity="error",
                line=raw.rstrip(),
            ))

    task = Task(
        text=text,
        done=done,
        in_progress=in_progress,
        cancelled=cancelled,
        time_min=time_min,
        blocked=blocked,
        raw_meta=meta_raw,
        line_no=line_no,
    )
    return task, warns


def _build_task_tree(
    lines: list[tuple[int, str]],   # (line_no, raw_line_with_indent)
) -> tuple[list[Task], list[ParseWarning]]:
    """
    Build a task tree from a list of (line_no, raw_line) pairs.
    Detects and reports:
      - inconsistent indentation (not a multiple of the established unit)
      - indent jumps (skipping a level)
      - indented task with no parent
      - time annotation on a non-leaf node
    """
    warns: list[ParseWarning] = []
    indent_unit: Optional[int] = None
    root_tasks: list[Task] = []
    stack: list[tuple[int, Task]] = []   # (level, task)

    for line_no, raw_line in lines:
        stripped = raw_line.lstrip(" ")
        leading  = len(raw_line) - len(stripped)

        task, task_warns = _parse_task_line(stripped, line_no)
        warns.extend(task_warns)
        if task is None:
            continue

        if leading == 0:
            # Root-level task — reset stack
            stack = [(0, task)]
            root_tasks.append(task)
            continue

        # ── Establish indent unit on first indented line ──────────────
        if indent_unit is None:
            indent_unit = leading

        # ── Validate indent size ──────────────────────────────────────
        if leading % indent_unit != 0:
            warns.append(ParseWarning(
                line_no=line_no,
                message=(
                    f"Indentation of {leading} spaces is not a multiple of "
                    f"{indent_unit} (the indent size established on the first "
                    f"indented task). Task may be misplaced."
                ),
                severity="error",
                line=raw_line.rstrip(),
            ))
            level = max(1, round(leading / indent_unit))
        else:
            level = leading // indent_unit

        # ── Guard: no parent exists at all ───────────────────────────
        if not stack:
            warns.append(ParseWarning(
                line_no=line_no,
                message="Indented task has no parent task above it.",
                severity="error",
                line=raw_line.rstrip(),
            ))
            root_tasks.append(task)
            stack = [(level, task)]
            continue

        parent_level = stack[-1][0]

        # ── Guard: indent jump skips a level ─────────────────────────
        if level > parent_level + 1:
            warns.append(ParseWarning(
                line_no=line_no,
                message=(
                    f"Indentation jumps from level {parent_level} to "
                    f"level {level} — expected level {parent_level + 1}. "
                    f"Treating as level {parent_level + 1}."
                ),
                severity="error",
                line=raw_line.rstrip(),
            ))
            level = parent_level + 1

        # ── Pop stack to the right parent ─────────────────────────────
        while stack and stack[-1][0] >= level:
            stack.pop()

        if stack:
            stack[-1][1].children.append(task)
        else:
            root_tasks.append(task)

        stack.append((level, task))

    # ── Post-parse: validate task tree consistency ────────────────────
    _validate_task_tree(root_tasks, warns)

    return root_tasks, warns


def _validate_task_tree(
    tasks: list[Task], warns: list[ParseWarning]
) -> None:
    """Recursively validate task tree: time-on-parent, done-blocked, done-parent-with-incomplete-children."""
    for t in tasks:
        # Time annotation on a non-leaf node will be ignored
        if t.children and t.time_min > 0:
            warns.append(ParseWarning(
                line_no=t.line_no,
                message=(
                    f"Task '{t.text[:60]}' has both subtasks and a time "
                    f"annotation (t:{t.time_min}m). The parent time will be "
                    f"ignored — subtask times will be summed instead."
                ),
                severity="warning",
            ))

        # Rule 3: blocked + done is contradictory
        if t.blocked and t.done:
            warns.append(ParseWarning(
                line_no=t.line_no,
                message=(
                    f"Task '{t.text[:60]}' is marked done [x] but also "
                    f"annotated as (blocked) — these are contradictory."
                ),
                severity="error",
                line="",
            ))

        # Rule 2: parent done but has incomplete children
        if t.done and t.children:
            incomplete = [
                c for c in t.children
                if not c.done and not c.cancelled
            ]
            if incomplete:
                sample = ", ".join(f"'{c.text[:30]}'" for c in incomplete[:3])
                warns.append(ParseWarning(
                    line_no=t.line_no,
                    message=(
                        f"Task '{t.text[:60]}' is marked done but has "
                        f"{len(incomplete)} incomplete subtask(s): {sample}."
                    ),
                    severity="error",
                ))

        _validate_task_tree(t.children, warns)


def _parse_config_table(lines: list[str]) -> WorklogConfig:
    cfg = WorklogConfig()
    for line in lines:
        m = RE_CONFIG_ROW.match(line.strip())
        if not m:
            continue
        key   = m.group(1).strip().lower()
        value = m.group(2).strip()

        if key == "target hours":
            try:
                cfg.target_hours = float(value)
            except ValueError:
                pass
        elif key == "baseline hours":
            try:
                cfg.baseline_hours = float(value)
            except ValueError:
                pass

    return cfg


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse(path: str | Path) -> Worklog:
    text  = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()

    title   = ""
    weeks: list[Week] = []
    config  = WorklogConfig()
    all_warnings: list[ParseWarning] = []

    current_section = None          # "week" | "config" | None
    current_week: Optional[Week]  = None
    current_day:  Optional[Day]   = None
    pending_task_lines: list[tuple[int, str]] = []
    config_lines: list[str] = []

    def flush_day() -> None:
        """Finalize the current day: build its task tree and append to week."""
        nonlocal pending_task_lines
        if current_day is None:
            return
        tasks, warns = _build_task_tree(pending_task_lines)
        all_warnings.extend(warns)
        current_day.tasks = tasks
        if current_week is not None:
            current_week.days.append(current_day)
        pending_task_lines = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()

        # ── Top-level title ───────────────────────────────────────────
        if line.startswith("# ") and not line.startswith("## "):
            if not title:
                title = line[2:].strip()
            continue

        # ── Week header ───────────────────────────────────────────────
        m_week = RE_WEEK.match(line)
        if m_week:
            flush_day()
            current_day = None
            current_week = Week(iso_week=m_week.group(1))
            weeks.append(current_week)
            current_section = "week"
            continue

        # ── Generic ## section ────────────────────────────────────────
        m_sec = RE_SECTION.match(line)
        if m_sec:
            flush_day()
            current_day = None
            sec_name = m_sec.group(1).strip().lower()
            current_section = "config" if sec_name == "config" else None
            current_week = None
            continue

        # ── Day header (### YYYY-MM-DD) ───────────────────────────────
        if current_section == "week":
            m_day = RE_DAY.match(line)
            if m_day:
                flush_day()
                current_day = Day(
                    date=date.fromisoformat(m_day.group(1)),
                    line_no=line_no,
                )
                continue

            # Accumulate task lines (at any indent level)
            if current_day is not None and line.lstrip().startswith("- ["):
                pending_task_lines.append((line_no, line))
            continue

        # ── Config section lines ──────────────────────────────────────
        if current_section == "config":
            config_lines.append(line)

    # Final flush
    flush_day()

    if config_lines:
        config = _parse_config_table(config_lines)

    # ── Rule 1: all past days must be fully complete ───────────────────
    today_date = date.today()
    for week in weeks:
        for day in week.days:
            if day.date >= today_date:
                continue
            incomplete = [
                t for t in _iter_leaves(day.tasks)
                if not t.done and not t.cancelled
            ]
            if incomplete:
                sample = ", ".join(f"'{t.text[:30]}'" for t in incomplete[:3])
                suffix = f" (and {len(incomplete) - 3} more)" if len(incomplete) > 3 else ""
                all_warnings.append(ParseWarning(
                    line_no=day.line_no,
                    message=(
                        f"Past day {day.date.isoformat()} has {len(incomplete)} "
                        f"incomplete task(s): {sample}{suffix}. "
                        f"All tasks in past days should be marked done or cancelled."
                    ),
                    severity="warning",
                ))

    return Worklog(
        title=title or "Work Log",
        weeks=weeks,
        config=config,
        warnings=all_warnings,
    )


# ---------------------------------------------------------------------------
# JSON-serialisable summary (used by /worklog/data)
# ---------------------------------------------------------------------------

def to_json(worklog: Worklog) -> dict:
    today = date.today()

    days_data: list[dict] = []
    today_data: Optional[dict] = None

    for week in worklog.weeks:
        for day in week.days:
            entry = {
                "date":        day.date.isoformat(),
                "week":        _iso_week(day.date),
                "time_min":    day.total_time_min,
                "time_h":      round(day.total_time_min / 60, 2),
            }
            if day.date == today:
                today_data = {
                    **entry,
                    "blocked": [t.text for t in day.blocked_tasks],
                    "pending": [
                        t.text for t in _iter_leaves(day.tasks)
                        if not t.done and not t.cancelled
                    ],
                }
            else:
                days_data.append(entry)

    # Sort ascending for the graph
    days_data.sort(key=lambda d: d["date"])

    # Summary stats (exclude today — it's partial)
    completed_days = [d for d in days_data if d["time_min"] > 0]
    avg_min = (
        sum(d["time_min"] for d in completed_days) / len(completed_days)
        if completed_days else 0
    )
    best = max((d["time_min"] for d in completed_days), default=0)

    WORK_DAYS_PER_WEEK = 5
    baseline_h = worklog.config.baseline_hours

    return {
        "title":              worklog.title,
        "target_hours":       worklog.config.target_hours,
        "target_min":         int(worklog.config.target_hours * 60),
        "weekly_target_h":    worklog.config.target_hours * WORK_DAYS_PER_WEEK,
        "baseline_hours":     baseline_h,
        "baseline_min":       int(baseline_h * 60),
        "weekly_baseline_h":  baseline_h * WORK_DAYS_PER_WEEK,
        "has_baseline":       baseline_h > 0,
        "today":              today_data,
        "days":               days_data,
        "avg_min":            round(avg_min),
        "avg_h":              round(avg_min / 60, 2),
        "best_min":           best,
        "best_h":             round(best / 60, 2),
        "total_days_logged":  len(completed_days),
        "warnings": [
            {
                "line_no":  w.line_no,
                "message":  w.message,
                "severity": w.severity,
                "line":     w.line,
            }
            for w in worklog.warnings
        ],
    }


def _iso_week(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
