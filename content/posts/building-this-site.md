---
title: Building This Site
date: 2026-04-15
tags: meta, fastapi, python
draft: false
---

I've wanted a personal site for years. Not a landing page — a proper place to put things. Writing, images, books, money. The usual private stuff made slightly less private by existing on a server somewhere.

## Why FastAPI

FastAPI is fast to write and fast to run. The automatic validation via Pydantic is useful even when you're not building an API, and the dependency injection system makes auth clean. You declare `user = Depends(require_auth)` and the framework handles the redirect. No middleware tangled through every route.

The alternative was Flask. Flask is fine. But FastAPI's async support is native rather than bolted on, and I'd rather write in the right abstraction from the start.

## Why SQLite

This is a personal site. One user, one machine, maybe one concurrent reader. SQLite is the correct choice. It's a file. You can copy it. You can open it in any SQLite browser and see your data. There's no daemon to restart, no connection pool to tune, no credentials to rotate.

I write Postgres-compatible queries so the migration cost is low if load ever becomes a real concern. It won't.

## Why Not WordPress

WordPress is a content management system pretending to be a website. I wanted a website. The difference matters. With WordPress you fight the system constantly — the theme is wrong, the plugin does too much, the database has forty tables for a blog. Here, a blog post is a Markdown file in a directory. That's it.

## What's Next

Gallery, expenses tracking, and a proper health section. The bones are here. The rest is just building rooms.
