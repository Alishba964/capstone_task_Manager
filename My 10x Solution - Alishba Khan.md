# My 10x Solution - Alishba Khan

**Project:** Capstone Task Manager
**Repository:** https://github.com/Alishba964/capstone_task_Manager

## What problem am I solving?

A basic to-do list is either public — anyone can see or edit anyone's tasks, with no login at all — or, if it does have a login, it gives no feedback beyond the raw list. People forget what they finished last week, lose track of their own progress, and have no lightweight way to check in on themselves without opening the app and scrolling through everything manually.

This affects anyone managing personal tasks who wants their data private and some sense of progress over time — students, freelancers, or small teams who don't want (or can't justify) a full project-management tool just to track a personal task list.

**The 10x claim:** instead of a to-do list that is either exposed or silent, this becomes a private, self-reporting task manager. Every user's data is isolated and secure, repeated reads are fast because they're cached, and at any moment a user can generate a clear PDF summary of what they've completed and what's still open — no manual scrolling required.

## How did I implement my solution?

The system is a FastAPI backend backed by PostgreSQL, with Supabase handling authentication. It implements 5 concepts from the program:

1. **API endpoints** — Full CRUD (`GET/POST /tasks`, `PUT/DELETE /tasks/{id}`), plus `/auth/signup`, `/auth/login`, and `/reports/summary`.
2. **Database** — PostgreSQL running in Docker, with a `tasks` table where every row is linked to a `user_id`.
3. **Authentication** — Supabase issues a JWT on login. A FastAPI dependency (`get_current_user`) verifies that token on every protected route and rejects missing/invalid tokens with a 401, before any route logic runs.
4. **Caching** — `GET /tasks` responses are cached in memory per user for 30 seconds, avoiding a database hit on every read. Any write (create, update, delete) immediately invalidates that user's cache entry, so the API never serves stale data after a change.
5. **Reporting** — `GET /reports/summary` counts each user's total/completed/pending tasks and streams back a generated PDF (via `fpdf2`) as a downloadable file.

Every task-related query is scoped with `WHERE user_id = ...`, so one user can never read, edit, or delete another user's data — this was tested directly by creating tasks under two different accounts and confirming each only ever sees their own.

**Steps to run it:** covered in full in the repository's `README.md`, including Docker/Postgres setup, Supabase configuration, and a 5-minute curl-based demo path. No frontend was built — the API is tested through Swagger UI (`/docs`) and curl, in line with the project's realistic scope guidance.
