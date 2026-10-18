"""Idea Harbour: a consent-based idea programme for students and researchers.

A team describes its idea in a short form and instantly gets an honest readiness read: what is strong,
what is only claimed, what is unknown and the exact next check, plus the programmes that fit. With the
team's consent the idea joins A'Pelago's review queue next to pre-company projects found in public data
(hackathon results, EU research projects), ranked by one transparent rubric so the team reviews a
handful, not thousands.

- models.py: the contracts (IdeaSubmission in, IdeaAssessment out, the queue).
- text.py: cleaning visitor text, quotable sentences, instructions aimed at the reviewer, similarity.
- rubric.py: the rule-based vetting (works with no model key): criteria, bands, tiers and the ledger.
- signals.py: the claims the rules find, each quoted from the team's own words; negated ones earn nothing.
- vocabulary.py: the words behind the signals, in English, Finnish and Swedish.
- nextsteps.py: programmes and funding routes from data/seed/grants.json (never invented).
- vet.py: one entry point; optionally lets a model add quoted claims, always falls back to the rules.
- pipeline.py: hackathon results and research projects as pre-company leads, organisation routes only.
- queue.py: A'Pelago's review queue: ranking, near-duplicates and the "Top N" cut; also the separate
  sample-data preview of invented ideas (data/ideas/sample_ideas.json).
- store.py: shared ideas live in memory per browser session for 60 minutes.
"""
