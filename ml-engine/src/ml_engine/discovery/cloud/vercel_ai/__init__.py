"""Vercel: one team's projects, read through Vercel's REST API, and nothing else.

The first cloud connector that speaks plain HTTP rather than a provider SDK. What is
here is the bearer-token client for the three read-only calls a scan makes (projects,
each project's environment variable NAMES, the team's integration configurations) and
the heuristic that decides which projects are agents.
"""
