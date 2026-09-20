"""Accounts, sessions and per-user progress for the hosted deployment.

Kept out of `api/` on purpose: Vercel treats every file under `api/` as its own
serverless function, so helper modules have to live somewhere else or they get
built as endpoints that answer nothing.
"""
