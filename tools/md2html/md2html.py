#!/usr/bin/env python3
"""md2html — ASCII flowchart to Mermaid converter.

Sister tool of md2docx.  Supports four ASCII diagram styles commonly found
in Markdown design documents:

1. Bracket flow:    [Node] + ↓ annotations
2. Numbered flow:   01 Node + ↓ annotations
3. Domain flow:     text containing "域：" + ↓ annotations
4. Sequence flow:   plain steps separated by ↓ with optional ├── branches

Usage:
    python md2html.py input.md output.md
    python md2html.py --html input.md output.html
    cat input.md | python md2html.py > output.md
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import Callable


__version__ = "1.0.0"


def sanitize_mermaid_text(text: str) -> str:
    """Make text safe for Mermaid node/edge labels."""
    text = text.replace("\\", " ")
    text = text.replace('"', "'")
    text = text.replace("|", "｜")
    # Keep <br/> but escape other bare < > to avoid HTML parsing issues.
    text = text.replace("<br/>", "\x00BR\x00").replace("<br>", "\x00BR\x00")
    text = text.replace("<", "＜").replace(">", "＞")
    text = text.replace("\x00BR\x00", "<br/>")
    return text.strip()


def _has_arrow(text: str) -> bool:
    return "↓" in text or "->" in text or "-->" in text


def looks_like_bracket_flow(text: str) -> bool:
    lines = text.splitlines()
    return any(re.match(r"^\[", l.strip()) for l in lines) and _has_arrow(text)


def looks_like_numbered_flow(text: str) -> bool:
    lines = text.splitlines()
    return any(re.match(r"^\d{2}\s+", l.strip()) for l in lines) and _has_arrow(text)


def looks_like_domain_flow(text: str) -> bool:
    lines = text.splitlines()
    return any("域：" in l for l in lines) and _has_arrow(text)


def looks_like_sequence_flow(text: str) -> bool:
    """Top-down sequence with optional branches: steps separated by ↓ and/or ├──."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    has_down = any("↓" in l for l in lines)
    has_box = any(c in text for c in "┌┐")
    if has_box:
        return False
    first = lines[0].strip()
    if first.startswith(("```", "[", "┌", "└", "│", "├──", "└──")):
        return False
    if not has_down:
        return False
    steps = 0
    for l in lines:
        s = l.strip()
        if s.startswith(("├──", "└──", "│")):
            continue
        if re.match(r"^[↓\-→\s]+$", s):
            continue
        if s:
            steps += 1
    return steps >= 2


def _strip_prefix(s: str) -> str:
    s = re.sub(r"^[↓\-→\s]+", "", s)
    s = re.sub(r"\s*[↓\-→]+\s*$", "", s)
    return s.strip()


def convert_bracket_flow(text: str, prefix: str) -> str | None:
    lines = text.splitlines()
    nodes: list[tuple[str, str]] = []
    edges: list[tuple[str, str, str]] = []
    annotations: list[str] = []
    last_node: str | None = None

    for line in lines:
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^\[([^\]]+)\](.*)", s)
        if m:
            label = sanitize_mermaid_text(m.group(1) + m.group(2))
            nid = f"{prefix}N{len(nodes)}"
            nodes.append((nid, label))
            if last_node is not None:
                elabel = "<br/>".join(sanitize_mermaid_text(a) for a in annotations) if annotations else ""
                edges.append((last_node, nid, elabel))
                annotations = []
            last_node = nid
            continue
        if s.startswith("↓") or s.startswith("->") or s.startswith("-->") or re.match(r"^[├└│]", s):
            rest = re.sub(r"^[↓├└─│\s]+", "", s).strip()
            if rest:
                annotations.append(rest)
            continue
        if annotations:
            annotations[-1] += " " + s

    if not nodes:
        return None

    out = ["flowchart TD"]
    for nid, label in nodes:
        out.append(f'  {nid}["{label}"]')
    for a, b, label in edges:
        if label:
            out.append(f'  {a} -->|"{label}"| {b}')
        else:
            out.append(f"  {a} --> {b}")
    return "\n".join(out)


def convert_numbered_flow(text: str, prefix: str) -> str | None:
    lines = text.splitlines()
    nodes: list[tuple[str, str]] = []
    edges: list[tuple[str, str, str]] = []
    annotations: list[str] = []
    last_node: str | None = None

    for line in lines:
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(\d{2})\s+(.+)", s)
        if m:
            label = sanitize_mermaid_text(m.group(2))
            nid = f"{prefix}N{len(nodes)}"
            nodes.append((nid, label))
            if last_node is not None:
                elabel = "<br/>".join(sanitize_mermaid_text(a) for a in annotations) if annotations else ""
                edges.append((last_node, nid, elabel))
                annotations = []
            last_node = nid
            continue
        if "↓" in s:
            rest = re.sub(r".*↓\s*", "", s).strip("（）()")
            if rest:
                annotations.append(rest)

    if not nodes:
        return None

    out = ["flowchart TD"]
    for nid, label in nodes:
        out.append(f'  {nid}["{label}"]')
    for a, b, label in edges:
        if label:
            out.append(f'  {a} -->|"{label}"| {b}')
        else:
            out.append(f"  {a} --> {b}")
    return "\n".join(out)


def convert_domain_flow(text: str, prefix: str) -> str | None:
    lines = text.splitlines()
    nodes: list[tuple[str, str]] = []
    edges: list[tuple[str, str, str]] = []
    annotations: list[str] = []
    last_node: str | None = None

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if "域：" in s and not s.startswith("↓") and not re.match(r"^[├└─│]", s):
            label = sanitize_mermaid_text(s)
            nid = f"{prefix}N{len(nodes)}"
            nodes.append((nid, label))
            if last_node is not None:
                elabel = "<br/>".join(sanitize_mermaid_text(a) for a in annotations) if annotations else ""
                edges.append((last_node, nid, elabel))
                annotations = []
            last_node = nid
            continue
        if s.startswith("↓") or s.startswith("├──") or s.startswith("└──") or s.startswith("│"):
            rest = re.sub(r"^[↓├└─│\s]+", "", s).strip()
            if rest:
                annotations.append(rest)
            continue
        if annotations:
            annotations[-1] += " " + s

    if not nodes:
        return None

    out = ["flowchart TD"]
    for nid, label in nodes:
        out.append(f'  {nid}["{label}"]')
    for a, b, label in edges:
        if label:
            out.append(f'  {a} -->|"{label}"| {b}')
        else:
            out.append(f"  {a} --> {b}")
    return "\n".join(out)


def convert_sequence_flow(text: str, prefix: str) -> str | None:
    """Convert a vertical-arrow sequence with optional tree branches into Mermaid."""
    lines = text.splitlines()
    parsed: list[tuple[str, list[str]]] = []
    pending_branches: list[str] = []
    last_main: str | None = None

    def is_branch_line(s: str) -> bool:
        return bool(re.match(r"^[\s]*([├└]──|│)", s))

    def is_main_line(s: str) -> bool:
        s = s.strip()
        if not s:
            return False
        if re.match(r"^[↓\-→\s]+$", s):
            return False
        if s.startswith(("```", "[", "┌", "└", "│", "├──", "└──")):
            return False
        return True

    for line in lines:
        if is_branch_line(line):
            rest = re.sub(r"^[\s]*[├└]──\s*", "", line)
            rest = re.sub(r"^[\s]*│\s*", "", rest)
            rest = _strip_prefix(rest)
            if rest:
                pending_branches.append(rest)
        elif is_main_line(line):
            if last_main is not None:
                parsed.append((last_main, pending_branches))
                pending_branches = []
            last_main = _strip_prefix(line)

    if last_main is not None:
        parsed.append((last_main, pending_branches))

    if len(parsed) < 2 and not any(b for _, b in parsed):
        return None

    out = ["flowchart TD"]
    node_idx = 0

    def make_node(label: str) -> str:
        nonlocal node_idx
        nid = f"{prefix}N{node_idx}"
        node_idx += 1
        out.append(f'  {nid}["{sanitize_mermaid_text(label)}"]')
        return nid

    prev_nodes: list[str] = []
    for i, (step, branches) in enumerate(parsed):
        current = make_node(step)
        for p in prev_nodes:
            out.append(f"  {p} --> {current}")
        prev_nodes = [current]
        if branches:
            branch_end_nodes = []
            for branch in branches:
                bnode = make_node(branch)
                out.append(f"  {current} --> {bnode}")
                branch_end_nodes.append(bnode)
            if i + 1 < len(parsed):
                prev_nodes = branch_end_nodes
            else:
                prev_nodes = branch_end_nodes

    return "\n".join(out)


def convert_diagram_to_mermaid(text: str, prefix: str) -> str | None:
    text = html.unescape(text)
    converters: list[tuple[Callable[[str], bool], Callable[[str, str], str | None]]] = [
        (looks_like_bracket_flow, convert_bracket_flow),
        (looks_like_numbered_flow, convert_numbered_flow),
        (looks_like_domain_flow, convert_domain_flow),
        (looks_like_sequence_flow, convert_sequence_flow),
    ]
    for detector, converter in converters:
        if detector(text):
            return converter(text, prefix)
    return None


def transform_markdown(text: str, prefix: str = "diagram_") -> str:
    """Convert ASCII flowcharts inside plain Markdown code blocks into Mermaid blocks."""
    # Find fenced code blocks with no language tag.
    pattern = re.compile(r"```\n(.*?)\n```", re.DOTALL)
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        code = match.group(1)
        current_prefix = f"{prefix}{counter}_"
        mermaid_src = convert_diagram_to_mermaid(code, current_prefix)
        counter += 1
        if mermaid_src:
            return f"```mermaid\n{mermaid_src}\n```"
        return match.group(0)

    return pattern.sub(repl, text)


def wrap_html(title: str, markdown_html: str, theme: str = "default") -> str:
    """Wrap pre-rendered markdown HTML into a minimal HTML page with Mermaid.js."""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }}
    pre {{ background: #f5f5f5; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f0f0f0; }}
    .mermaid {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem; margin: 1rem 0; overflow-x: auto; text-align: center; }}
  </style>
</head>
<body>
  {markdown_html}
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{ startOnLoad: true, theme: '{theme}' }});
  </script>
</body>
</html>
"""


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Convert ASCII flowcharts in Markdown to Mermaid.")
    parser.add_argument("input", nargs="?", help="Input Markdown file (default: stdin)")
    parser.add_argument("output", nargs="?", help="Output file (default: stdout)")
    parser.add_argument("--html", action="store_true", help="Output a full HTML page instead of Markdown")
    parser.add_argument("--title", default="Converted Document", help="HTML page title (used with --html)")
    parser.add_argument("--theme", default="default", help="Mermaid theme (used with --html)")
    args = parser.parse_args()

    if args.input and args.input != "-":
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    transformed = transform_markdown(text)

    if args.html:
        try:
            import markdown as md_lib
        except ImportError as exc:
            print("ERROR: --html requires the 'markdown' Python package.", file=sys.stderr)
            return 1
        html_body = md_lib.markdown(transformed, extensions=["tables", "fenced_code", "toc"])
        output = wrap_html(args.title, html_body, args.theme)
    else:
        output = transformed

    if args.output and args.output != "-":
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
