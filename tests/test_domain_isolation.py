"""Guards the vertical-slice structure in app/: user, goal, profile, and
swim_time are independent domains today (verified by grep before this test was
added), and should stay that way rather than silently growing a cross-domain
dependency that then anchors future decisions. auth, stats, and rag are
deliberately excluded - they're aggregator domains that legitimately read from
one or more of these base domains (auth reads user, stats reads user and
swim_time, rag reads goal and profile), so a base domain never needs to import
one of them back."""

import ast
from pathlib import Path

BASE_DOMAINS = {"user", "goal", "profile", "swim_time"}
APP_ROOT = Path(__file__).resolve().parent.parent / "app"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}


def test_base_domains_do_not_import_each_other():
    violations = []
    for domain in BASE_DOMAINS:
        for py_file in (APP_ROOT / domain).glob("*.py"):
            for module in _imported_modules(py_file):
                parts = module.split(".")
                if module.startswith("app.") and len(parts) > 1 and parts[1] in BASE_DOMAINS and parts[1] != domain:
                    violations.append(f"{py_file.relative_to(APP_ROOT.parent)} imports {module}")
    assert not violations, "Cross-domain imports found:\n" + "\n".join(violations)
