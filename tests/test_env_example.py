"""Every environment variable the app reads is documented in .env.example."""

import re

from bluewatch.config import ROOT

ENV_NAME = re.compile(r"""["']((?:BLUEWATCH|OUTREACH|SMTP|ANTHROPIC)_[A-Z0-9_]+)["']""")


def test_env_example_lists_every_variable_the_code_reads():
    sources = [path.read_text(encoding="utf-8") for path in (ROOT / "bluewatch").rglob("*.py")]
    read = {name for text in sources for name in ENV_NAME.findall(text)}
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z0-9_]+)=", example, re.MULTILINE))
    assert read, "the pattern found no variables at all"
    assert read <= documented, f"missing from .env.example: {sorted(read - documented)}"
