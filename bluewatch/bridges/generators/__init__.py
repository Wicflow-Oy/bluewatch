"""One generator per bridge type. Each reads only recorded data and returns list[Bridge]."""

from __future__ import annotations

from datetime import date

from bluewatch.bridges.generators.funding import programme_fit, proof_step, rule_decides
from bluewatch.bridges.generators.procurement import won_before_open_again
from bluewatch.bridges.generators.projects import already_works_with, lab_window
from bluewatch.bridges.generators.regulation import law_creates_buyer
from bluewatch.models import Bridge

GENERATORS = (
    won_before_open_again,
    already_works_with,
    rule_decides,
    proof_step,
    law_creates_buyer,
    programme_fit,
    lab_window,
)

__all__ = [g.__name__ for g in GENERATORS] + ["GENERATORS", "generate_all"]


def generate_all(*, today: date | None = None) -> list[Bridge]:
    return [bridge for generator in GENERATORS for bridge in generator(today=today)]
