import re
import subprocess
from pathlib import Path

SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"ghp_[0-9A-Za-z_]{20,}"),
    re.compile(r"github_pat_[0-9A-Za-z_]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
)


def test_tracked_files_do_not_contain_obvious_secrets() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    paths = [Path(raw.decode()) for raw in result.stdout.split(b"\0") if raw]

    matches: list[str] = []
    for path in paths:
        full_path = root / path
        if full_path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
            continue
        text = full_path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                matches.append(str(path))

    assert matches == []
