from __future__ import annotations

from bluewatch.ideas.models import IdeaSubmission, TeamMember

SESSION = "test-session-0123456789ab"
OTHER_SESSION = "other-session-0123456789ab"


def strong_submission(**changes) -> IdeaSubmission:
    """A complete, specific student idea (invented for tests; never shown in the app)."""
    base = IdeaSubmission(
        title="FeedSense for fish farms",
        problem="Fish farms in the Archipelago Sea overfeed by about 15%, which wastes feed and adds nutrients "
        "to the sea. New nutrient rules from 2027 make this costly.",
        who_has_it="Rainbow trout farms in the Turku archipelago and on Åland.",
        solution="An underwater camera and a small machine-learning model detect when fish stop eating and stop "
        "the feeder, instead of feeding on a fixed timetable.",
        who_pays="Farms pay a subscription per site, about 300 EUR a month.",
        impact_area="A Clean Ocean",
        exists=["prototype", "user_interviews"],
        exists_detail="We tested a prototype at one farm in Kustavi in August 2026 for three weeks. We interviewed "
        "9 farm managers.",
        needs=["pilot_partner", "mentors"],
        team=[
            TeamMember(role="build", skills="embedded ML"),
            TeamMember(role="business", skills="economics"),
            TeamMember(role="domain", skills="aquaculture MSc"),
        ],
        commitment="part_time",
        country="FI",
        links=["https://example.org/feedsense"],
    )
    return base.model_copy(update=changes)


def payload(sub: IdeaSubmission) -> dict:
    return sub.model_dump(mode="json")
