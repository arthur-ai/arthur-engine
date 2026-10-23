"""Vercel: one team's projects, read through Vercel's REST API, and nothing else.

The first cloud connector that speaks plain HTTP rather than a provider SDK. What is
here is the bearer-token client for the read-only calls a scan makes -- the inventory
(projects, each project's environment variable NAMES, the team's integration
configurations) and the extra signals that add recall (team-shared variable names,
Agent Runs, Observability Plus metrics and, when the source opts in, the package.json of
a non-Git production deployment) -- and the heuristic that decides which projects are
agents.
"""
