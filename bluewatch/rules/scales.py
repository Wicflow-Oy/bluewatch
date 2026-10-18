"""The four readiness scales as public-evidence cues, written from the documented scale tables
(EU TRL, KTH Innovation Readiness Level), not fitted to any answer key.

Each cue is (level, regex, what it shows). A level needs a fact whose claim matches the cue; the
highest supported level wins. Patterns run on lower-cased claim text.
"""

from __future__ import annotations

Cue = tuple[int, str, str]

# TRL 1-9, the EU technology readiness scale.
TRL_CUES: tuple[Cue, ...] = (
    (
        9,
        r"\binstalled on \d+ (vessels|ships)\b|\boperational constellation\b|\bfleet roll-?outs?\b"
        r"|\b(multiple|several) commercial deployments\b",
        "multiple commercial deployments",
    ),
    (
        8,
        r"\b(type|class|product) (approval|certification)\b|\btype-approved\b"
        r"|\bcertified by (dnv|bureau veritas|lloyd)",
        "class or type approval",
    ),
    (
        8,
        r"\bon sale\b|\bonline store\b|\bsold (to|through dealers)\b|\bcommercial (product|deliveries|delivery|use)\b"
        r"|\bcommercial (passenger )?(ferry|vessel|service)\b|\bcustomer logos\b|\bpaying customers?\b",
        "first commercial deliveries",
    ),
    (
        7,
        r"\b(field|sea|harbour|harbor) (pilot|trial)s?\b|\bdemonstrator\b|\bdeployed (in|at)\b",
        "pilot or prototype in the operational environment",
    ),
    (
        6,
        r"\bpilot (phase|project|region|site)\b|\bfirst (european )?pilot\b|\bentering pilot\b|\bmoving into pilot\b"
        r"|\bdemo with\b|\blake demo\b|\btest basin\b|\binnovation action\b|\bpilot of up to\b",
        "demonstrated in a relevant environment",
    ),
    (
        4,
        r"\bprototype\b|\bproof[- ]of[- ]concept\b|\blab(oratory)? (test|tests|results|validation|scale)\b",
        "proof of concept or lab validation",
    ),
    (
        3,
        r"\btechnology development\b|\bunder development\b|\bdeveloping\b|\bdevelops\b|\bpatented\b",
        "technology in development",
    ),
    (2, r"\bconcept for\b|\bconcept\b(?! store)|\bplans? (drone|robot)|\bdescribes plans\b", "concept formulated"),
)

# "Field pilot with a named partner" (TRL 7): run on the original text, since a capital letter after
# "with" is what separates "a pilot with Adazu udens" from "a demo with a potential customer".
TRL_NAMED_PILOT = r"\bpilot\b[^.;]*\bwith [A-Z]"

# Services and non-technology consumer goods have no technology readiness.
SERVICE_CUES = (
    r"\bconsult(ing|ancy)\b|\badvisory\b|\btraining\b|\bproject (planning|management|execution)\b"
    r"|\bowner representation\b|\bmaintenance\b|\brepairs?\b|\bpolishing\b|\bwinter storage\b"
    r"|\bdesign for\b|\be-learning\b|\bsightseeing\b|\bcruises\b|\bdistributes\b|\bservice\b"
)
CONSUMER_CUES = (
    r"\bclothing\b|\bapparel\b|\bskincare\b|\bskin care\b|\bbody care\b|\baccessories\b"
    r"|\blures\b|\bcaviar\b"
)
TECH_CUES = (
    r"\bplatform\b|\bsoftware\b|\bapp\b|\bsaas\b|\bsensors?\b|\bdevices?\b|\bsystems?\b|\brobot|\bdrones?\b"
    r"|\btechnology\b|\bmachine\b|\banalyser\b|\bturbines?\b|\bai\b|\balgorithm|\bmaterials?\b|\bmanufactur"
    r"|\bdevelop|\bbuild|\bproduces?\b|\bconverts?\b|\bremoves?\b|\brecovers?\b|\bplatforms?\b"
)

# KTH business readiness 1-9 as public proxies; a public-contract award counts as test sales, since a buyer paid.
BRL_CUES: tuple[Cue, ...] = (
    (
        9,
        r"\bnet sales\b|\brevenue of\b|\bprofitab|\b(listed|public) company\b|\bnasdaq\b|\bworld'?s largest\b",
        "scaled, recurring revenue",
    ),
    (
        8,
        r"\b(dealers?|distributors?|distribution partners?) (in|across)\b|\bsold through dealers\b"
        r"|\bseveral markets\b|\bin \d+ countries\b",
        "channels and several markets",
    ),
    (
        7,
        r"\bcustomer logos\b|\bcustomers include\b|\binstalled base\b|\b\d+ ordered\b|\binstalled on \d+\b"
        r"|\bcase stud(y|ies)\b|\binvested in \d+\b",
        "named customers or repeat orders",
    ),
    (6, r"\bpaid pilot\b|\bfirst (customer|sale|invoice|order)\b|\bcontract with\b|\bcontract award\b", "test sales"),
    (
        5,
        r"\bpilot\b|\bletter of intent\b|\bloi\b|\bdemo with\b|\bnamed as (a )?partner\b|\bproject partner\b",
        "pilot, LOI or partner",
    ),
    (
        4,
        r"\bsubscription\b|\bpricing\b|\bprice\b|\bper (month|year|user)\b|\b\d+-day trial\b|\bfree trial\b",
        "pricing published",
    ),
    (3, r"\bmarket (size|sizing)\b|\btam\b|\bbusiness model\b", "market sized or business model drafted"),
)

# Investment readiness 1-9 as milestones visible in public data, up to the rounds Redstone Blue invests in.
IRL_CUES: tuple[Cue, ...] = (
    (
        9,
        r"\bseries [b-f]\b|\bseries a\b[^.;]*\b(closed|raised|round)\b|\b(listed|public) company\b|\bnasdaq\b"
        r"|\bacquired by\b",
        "Series A or later, listed or acquired",
    ),
    (8, r"\bseed (round|funding)\b|\bfunding round\b|\bround of about eur [1-9]", "seed round raised"),
    (
        6,
        r"\bshare issue registered\b|\bpre-seed\b|\bredstone-managed\b|\bredstone blue investment\b"
        r"|\b(growth )?fund \(|\bportfolio\b|\bnew capital\b",
        "equity event (share issue or fund investment)",
    ),
    (5, r"\blive product hostname\b|\bpilot\b[^.;]*\bwith\b|\bletter of intent\b", "pilot with a customer or MVP live"),
    (
        4,
        r"\bgrant\b|co-funded|\beu (funding|backing|co-funding)\b|\bvoucher\b|\bcohort\b|\bbatch member\b"
        r"|\baccelerator\b|\bselected for\b|\binnovator \d{4}\b|\breward\b|\bprogramme\b",
        "non-dilutive funding or an accelerator",
    ),
)

# Ocean (or other) impact, our own 1-5 scale per area: 1 intent, 2 KPI defined,
# 3 piloted, 4 validated, 5 embedded. Self-reported figures cap at 3.
IMPACT_MECHANISM = (
    r"\b(remov|reduc|cut|cutting|recover|replac|restor|captur|prevent|clean|avoid|regenerat"
    r"|zero-emission|low-impact|biodegradable|non-toxic|less harm)"
)
IMPACT_KPI = r"\d+(\.\d+)?\s?(%|percent|tonnes?|t co2|kg|mw|kw|m3)"
IMPACT_VALIDATED = r"\b(third-party|independently|verified by|validated by)\b"
IMPACT_EMBEDDED = r"\bimpact report\b|\breported (annually|yearly|every year)\b"

RAISE_BY = {
    "trl": {
        None: "A dated pilot or test with a named partner, or a class or type approval",
        2: "A prototype or lab result (TRL 3-4)",
        3: "A prototype or lab validation (TRL 4)",
        4: "A test in a relevant environment, such as a harbour trial or test basin (TRL 5-6)",
        6: "A field pilot with a named partner such as a port or ship operator (TRL 7)",
        7: "A class or type approval, or first commercial deliveries (TRL 8)",
        8: "Several commercial deployments (TRL 9)",
    },
    "brl": {
        None: "A public description of the offer (landing page or one-pager)",
        2: "A business model with revenue logic, such as published pricing (BRL 4)",
        3: "Published pricing or revenue logic (BRL 4)",
        4: "A pilot, LOI or named partner (BRL 5)",
        5: "A paid pilot, first invoice or public contract (BRL 6)",
        6: "Named customers or repeat orders (BRL 7)",
        7: "Distribution partners or several markets (BRL 8)",
        8: "Filed accounts with recurring revenue (BRL 9)",
    },
    "irl": {
        None: "A company register record (IRL 3)",
        3: "A grant or accelerator place (IRL 4), or a pilot with a named customer (IRL 5)",
        4: "A pilot or LOI with a named customer, or a live MVP (IRL 5)",
        5: "A registered share issue or first revenue (IRL 6)",
        6: "Repeatable traction and a complete core team (IRL 7); founder data needed",
        7: "A seed round (IRL 8); founder data needed",
        8: "Series A metrics (IRL 9: outside a pre-seed to Series A window)",
    },
    "oirl": {
        None: "The company's own impact claim mapped to an area (level 1)",
        1: "A named KPI with a unit and baseline (level 2)",
        2: "The KPI measured in a real pilot with a dated baseline (level 3)",
        3: "Repeat measurements with a third-party check (level 4); self-reported figures stop at 3",
        4: "Reporting against targets over several periods (level 5)",
    },
}


TOP_LEVEL = {"trl": 9, "brl": 9, "irl": 9, "oirl": 5}


def raise_by(key: str, level: int | None) -> str | None:
    table = RAISE_BY[key]
    if level is None:
        return table[None]
    if level >= TOP_LEVEL[key]:
        return None
    candidates = [lvl for lvl in table if lvl is not None and lvl <= level]
    return table[max(candidates)] if candidates else None
