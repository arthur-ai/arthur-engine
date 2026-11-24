"""Bitdefender GravityZone: a carrier that is asked, not read.

Every other endpoint carrier hands back an attribute the device already reported. A
GravityZone endpoint has nowhere to keep a 24 KB value (an endpoint label holds 64
characters), so this package asks each online endpoint for it: one read-only command
through the Investigation API, whose output is the `arthur1.` value the collector left
on disk. What is here is GravityZone's JSON-RPC, its endpoint listing and its command
lifecycle. Decoding, matching and the record shape are `discovery.endpoint`'s, unchanged.
"""
