"""The same idea reads the same in English, Finnish and Swedish, and a Finnish or Swedish read has no English."""

from __future__ import annotations

import pytest

from bluewatch import i18n
from bluewatch.api.ideas import idea_prose
from bluewatch.ideas import rubric
from bluewatch.ideas.models import IdeaSubmission, TeamMember
from bluewatch.ideas.nextsteps import check_why
from bluewatch.ideas.vet import vet
from tests.ideas.helpers import payload, strong_submission

# One idea, translated faithfully. It read "Bring now" in English and Finnish but "Promising" in Swedish:
# the sonar's verbs were no method in English or Swedish, and "spöknät" was no word for a clean ocean.
GHOST_NETS = {
    "en": dict(
        title="Ghost net finder",
        problem="Ghost nets lost by fishers keep killing fish and seals in the Archipelago Sea for years.",
        who_has_it="Coastal fishers and the regional environment centre.",
        solution="A side-scan sonar unit mounted on a small boat flags ghost nets on the seabed and logs each "
        "position for divers.",
        who_pays="The environment centre and fishing associations would pay per survey day.",
        exists_detail="A prototype unit tested on two boats found seven lost nets.",
    ),
    "fi": dict(
        title="Haamuverkkojen etsijä",
        problem="Kalastajien kadottamat haamuverkot tappavat kaloja ja hylkeitä Saaristomerellä vuosien ajan.",
        who_has_it="Rannikkokalastajat ja alueellinen ympäristökeskus.",
        solution="Pieneen veneeseen asennettu viistokaikuluotain tunnistaa haamuverkot merenpohjasta ja tallentaa "
        "jokaisen sijainnin sukeltajille.",
        who_pays="Ympäristökeskus ja kalastusalueet maksaisivat kartoituspäivää kohden.",
        exists_detail="Prototyyppiä testattiin kahdella veneellä, ja se löysi seitsemän kadonnutta verkkoa.",
    ),
    "sv": dict(
        title="Spöknätsfinnaren",
        problem="Spöknät som fiskare har tappat fortsätter att döda fisk och sälar i Skärgårdshavet i åratal.",
        who_has_it="Kustfiskare och det regionala miljöcentret.",
        solution="En sidoseende sonarenhet monterad på en liten båt upptäcker spöknät på havsbotten och loggar "
        "varje position åt dykarna.",
        who_pays="Miljöcentret och fiskeområdena skulle betala per kartläggningsdag.",
        exists_detail="En prototypenhet testades på två båtar och hittade sju förlorade nät.",
    ),
}
GHOST_NET_FORM = dict(
    impact_area="A Clean Ocean",
    exists=["prototype"],
    commitment="part_time",
    country="FI",
    team=[TeamMember(role="build"), TeamMember(role="domain")],
)

FEEDSENSE = {  # the tests' strong idea (helpers.strong_submission) in Finnish and Swedish
    "en": {},
    "fi": dict(
        title="FeedSense kalankasvattamoille",
        problem="Saaristomeren kalankasvattamot yliruokkivat noin 15 %, mikä tuhlaa rehua ja lisää ravinteita "
        "mereen. Uudet ravinnesäännöt vuodesta 2027 tekevät tästä kallista.",
        who_has_it="Kirjolohikasvattamot Turun saaristossa ja Ahvenanmaalla.",
        solution="Vedenalainen kamera ja pieni koneoppimismalli havaitsevat, kun kalat lakkaavat syömästä, ja "
        "pysäyttävät ruokintalaitteen sen sijaan, että ruokittaisiin kiinteän aikataulun mukaan.",
        who_pays="Kasvattamot maksavat kuukausimaksun laitosta kohden, noin 300 euroa kuukaudessa.",
        exists_detail="Testasimme prototyyppiä yhdellä kasvattamolla Kustavissa elokuussa 2026 kolmen viikon "
        "ajan. Haastattelimme 9 kasvattamon johtajaa.",
    ),
    "sv": dict(
        title="FeedSense för fiskodlingar",
        problem="Fiskodlingar i Skärgårdshavet överutfodrar med cirka 15 %, vilket slösar foder och tillför "
        "näringsämnen till havet. Nya regler om näringsämnen från 2027 gör detta kostsamt.",
        who_has_it="Regnbågslaxodlingar i Åbo skärgård och på Åland.",
        solution="En undervattenskamera och en liten maskininlärningsmodell upptäcker när fiskarna slutar äta och "
        "stoppar foderautomaten, i stället för att utfodra enligt ett fast schema.",
        who_pays="Odlingarna betalar ett abonnemang per anläggning, cirka 300 euro i månaden.",
        exists_detail="Vi testade en prototyp på en odling i Gustavs i augusti 2026 under tre veckor. Vi "
        "intervjuade 9 odlingschefer.",
    ),
}


def ghost_nets(lang: str) -> IdeaSubmission:
    return IdeaSubmission(**GHOST_NETS[lang], **GHOST_NET_FORM)


def feedsense(lang: str) -> IdeaSubmission:
    return strong_submission(**FEEDSENSE[lang])


def verdict(sub: IdeaSubmission, today) -> tuple:
    a = vet(sub, today=today)
    return a.tier, a.potential, a.evidence, {c.id: c.rung for c in a.criteria}


@pytest.mark.parametrize("idea", [ghost_nets, feedsense])
def test_the_same_idea_gets_the_same_read_in_every_language(idea, today):
    english, finnish, swedish = (verdict(idea(lang), today) for lang in ("en", "fi", "sv"))
    assert english == finnish == swedish
    assert english[0] == "bring_now"


def untranslated(data: dict, lang: str) -> list[str]:
    """Prose in an API answer with no entry in the language's table. Strengths are left out: each embeds the
    team's own words, and the page builds them from the translated criterion instead."""
    data = {key: value for key, value in data.items() if key != "strengths"}
    prose: list[str] = []
    i18n.walk(data, lambda text: prose.append(text) or text)
    idea_prose(data, lambda text: prose.append(text) or text)
    return [text for text in prose if text.strip() and i18n.pattern(text)[0] not in i18n.table(lang)]


@pytest.mark.parametrize("lang", ["fi", "sv"])
@pytest.mark.parametrize(
    "sub",
    [
        ghost_nets("en"),
        ghost_nets("sv"),
        feedsense("fi"),
        strong_submission(team=[TeamMember(role="design"), TeamMember(role="build")]),
        strong_submission(problem="", who_has_it="", links=[], exists=[]),
    ],
)
def test_a_read_in_finnish_or_swedish_has_no_english_sentence(client, lang, sub):
    english = client.post("/api/ideas/vet", json=payload(sub)).json()
    assert not untranslated(english, lang)


@pytest.mark.parametrize("lang", ["fi", "sv"])
def test_every_composed_sentence_of_a_read_is_translated(lang):
    """Sentences the rules put together from parts, which no single sample read reaches all of."""
    table = i18n.table(lang)
    for c in rubric.CRITERIA:
        for rung in (*c.rungs, "Not stated", *(["Relies on grants"] if c.id == "who_pays" else [])):
            assert i18n.pattern(check_why(c.label, rung))[0] in table
        for rung in c.rungs[2:] if c.id != "trace" else ():  # the public trace is never listed as a strength
            assert rubric.strength(c.label, rung) in table
    for potential in ("High", "Medium"):
        for evidence in ("thin", "some", "strong"):
            assert f"{potential} potential and {evidence} evidence: two answers would decide it." in table


@pytest.mark.parametrize("lang", ["fi", "sv"])
def test_a_strength_quoting_the_team_is_translated_around_the_quote(client, lang):
    sub = strong_submission(who_has_it="Harbour masters on the Turku archipelago ring road and their ferry crews.")
    english = client.post("/api/ideas/vet", json=payload(sub)).json()["strengths"]
    local = client.post(f"/api/ideas/vet?lang={lang}", json=payload(sub)).json()["strengths"]
    quoted = [(en, lo) for en, lo in zip(english, local, strict=True) if en.endswith('")')]
    assert quoted
    for en, lo in quoted:
        rule, quote = en[:-2].split(' ("', 1)
        assert lo == f"{i18n.localize_text(rule, lang)} (”{quote}”)" and lo != en


@pytest.mark.parametrize("lang", ["fi", "sv"])
def test_the_consent_boxes_are_translated(client, lang):
    form = client.get(f"/api/ideas/form?preset=blue&lang={lang}").json()
    assert not untranslated(client.get("/api/ideas/form?preset=blue").json(), lang)
    assert "Claude" in form["ai_read_text"] and "A'Pelago" in form["consent_text"]
