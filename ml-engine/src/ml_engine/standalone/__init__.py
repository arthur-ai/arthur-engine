"""Standalone discovery: one container, no Platform, no GenAI Engine.

Driven by a config file instead of dequeued jobs. Setting `ML_ENGINE_DISCOVERY_CONFIG` to
the file's path is what turns the mode on; without it the engine polls the Platform as
it always has. Each configured source is scanned on an interval by the same connectors
and scan loop a Platform job uses, and what they find is sent to one SIEM destination.
"""
