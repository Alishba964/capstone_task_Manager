# Capstone Task Manager — My 10x Solution

A private, self-reporting task manager. Every user's tasks are isolated and secured behind authentication, repeated reads are cached for speed, and each user can download a PDF summary of their progress on demand.

## The problem

A basic to-do list is either public (no login, anyone can see/edit any task) or, if it has login, gives no feedback beyond the raw list — so people forget what they finished and lose track of their own progress. This project closes that gap: every user gets a private, authenticated task list plus an on-demand progress report, without needing a full project-management tool.

## The 5 concepts implemented

| # | Concept | Where it lives in the code |
|---|---------|------------------------------|
| 1 | **API endpoints** | Full CRUD in `main.py` — `GET/POST /tasks`, `PUT/DELETE /tasks/{id}` |
| 2 | **Database** | PostgreSQL (Docker), `tasks` table with a `user_id` foreign key |
| 3 | **Authentication** | Supabase JWT — `/auth/signup`, `/auth/login`, and a `get_current_user` dependency protecting every task/report route |
| 4 | **Caching** | In-memory cache (30s TTL) on `GET /tasks`, invalidated on every write (create/update/delete) |
| 5 | **Reporting** | `GET /reports/summary` generates and streams a PDF (via `fpdf2`) with the user's task counts and list |



## How to run

### 1. Start Postgres in Docker
```bash
docker run --name capstone-postgres -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=capstonedb -p 5433:5432 -v capstone_pgdata:/var/lib/postgresql/data -d postgres:16
```

### 2. Set up a Supabase project
- Create a free project at [supabase.com](https://supabase.com).
- Under **Project Settings → API Keys**, copy your **Project URL** and **Publishable key**.

### 3. Configure environment variables
Copy `.env.example` to `.env` and fill in your own values:
```
DATABASE_URL=postgresql://postgres:devpassword@localhost:5433/capstonedb
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_publishable_key
```

### 4. Install dependencies and run
```bash
python3 -m venv venv
source venv/Scripts/activate   # Windows (Git Bash)
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

> **Note:** In Supabase's default settings, new signups may require email confirmation before login works. For quick local testing, this can be turned off under **Authentication → Providers → Email → Confirm email**.

## Endpoints

| Method | Path | Auth required | Description |
|--------|------|:---:|-------------|
| POST | `/auth/signup` | No | Create a new account |
| POST | `/auth/login` | No | Log in, returns an access token |
| GET | `/tasks` | Yes | List the logged-in user's tasks (cached) |
| POST | `/tasks` | Yes | Create a new task |
| PUT | `/tasks/{id}` | Yes | Update a task's title/done status |
| DELETE | `/tasks/{id}` | Yes | Delete a task |
| GET | `/reports/summary` | Yes | Download a PDF summary of the user's tasks |

## 5-minute demo path

1. **Sign up:**
   ```bash
   curl -i -X POST http://localhost:8000/auth/signup -H "Content-Type: application/json" -d '{"email":"demo@example.com","password":"password123"}'
   ```
2. **Log in** and copy the `access_token` from the response:
   ```bash
   curl -i -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"demo@example.com","password":"password123"}'
   ```
3. **Create a task** (replace `TOKEN` with your access token):
   ```bash
   curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d '{"title":"Try the demo"}'
   ```
4. **List your tasks** (first call hits the database, a second call within 30s is served from cache):
   ```bash
   curl -i http://localhost:8000/tasks -H "Authorization: Bearer TOKEN"
   ```
5. **Download a PDF report:**
   ```bash
   curl -i http://localhost:8000/reports/summary -H "Authorization: Bearer TOKEN" --output report.pdf
   ```
   Open `report.pdf` — it shows your task counts and list.

All of the above can also be run interactively from the Swagger UI at `/docs`, using the "Authorize" button to paste your token.

## Non-goal

No frontend UI was built — this is a clean, documented API, tested through Swagger UI and curl, in line with the project's realistic scope guidance.

## Notes

- Tasks are scoped per user — `WHERE user_id = ...` on every query — so one user can never read or modify another user's tasks.
- The `GET /tasks` cache has a 30-second TTL and is invalidated immediately on any create/update/delete, so writes are always reflected right away.
- `.env` is gitignored; see `.env.example` for the required format.
