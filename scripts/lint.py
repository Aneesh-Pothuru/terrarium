from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

for path in sorted((*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py"))):
    text = path.read_text(encoding="utf-8")
    try:
        ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        errors.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    for number, line in enumerate(text.splitlines(), 1):
        if line.rstrip() != line:
            errors.append(f"{path.relative_to(ROOT)}:{number}: trailing whitespace")

for path in sorted((*ROOT.glob("schemas/*.json"), *ROOT.glob("examples/**/*.json"))):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

if errors:
    raise SystemExit("\n".join(errors))
print("lint: AST, whitespace, and JSON checks passed")

