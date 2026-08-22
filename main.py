import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
from supabase import create_client, Client
import time
from fastapi.responses import Response
from fpdf import FPDF
import io

# ---------- Simple in-memory cache ----------
CACHE = {}
CACHE_TTL_SECONDS = 30


def get_cached_tasks(user_id):
    entry = CACHE.get(user_id)
    if entry is None:
        return None

    cached_data, cached_at = entry
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        del CACHE[user_id]
        return None

    return cached_data


def set_cached_tasks(user_id, data):
    CACHE[user_id] = (data, time.time())


def invalidate_cache(user_id):
    CACHE.pop(user_id, None)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


init_db()


# ---------- Auth dependency ----------
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")

    token = authorization.split(" ")[1]

    try:
        result = supabase.auth.get_user(token)
        return result.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------- Request models ----------
class TaskCreate(BaseModel):
    title: str


class AuthCredentials(BaseModel):
    email: str
    password: str


# ---------- Root ----------
@app.get("/")
def root():
    return {"name": "Capstone Task Manager", "status": "running"}


# ---------- Auth routes ----------
@app.post("/auth/signup", status_code=201)
def signup(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })
        return result.user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


# ---------- Task routes (protected) ----------
from fastapi import Depends

@app.get("/tasks")
def get_tasks(user=Depends(get_current_user)):
    cached = get_cached_tasks(user.id)
    if cached is not None:
        return cached

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE user_id = %s", (user.id,))
    rows = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()

    set_cached_tasks(user.id, rows)
    return rows


@app.post("/tasks", status_code=201)
def create_task(new_task: TaskCreate, user=Depends(get_current_user)):
    if not new_task.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (user_id, title, done) VALUES (%s, %s, %s) RETURNING *",
        (user.id, new_task.title, False)
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    invalidate_cache(user.id)
    return dict(row)


class TaskUpdate(BaseModel):
    title: str
    done: bool = False


@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated: TaskUpdate, user=Depends(get_current_user)):
    if not updated.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s", (task_id, user.id))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    cur.execute(
        "UPDATE tasks SET title = %s, done = %s WHERE id = %s AND user_id = %s RETURNING *",
        (updated.title, updated.done, task_id, user.id)
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    invalidate_cache(user.id)
    return dict(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s", (task_id, user.id))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user.id))
    conn.commit()
    cur.close()
    conn.close()
    invalidate_cache(user.id)
    return


@app.get("/reports/summary")
def get_summary_report(user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE user_id = %s", (user.id,))
    tasks = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()

    total = len(tasks)
    done = len([t for t in tasks if t["done"]])
    pending = total - done

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Task Summary Report", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"User: {user.email}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Total tasks: {total}", ln=True)
    pdf.cell(0, 8, f"Completed: {done}", ln=True)
    pdf.cell(0, 8, f"Pending: {pending}", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Tasks:", ln=True)
    pdf.set_font("Helvetica", "", 11)

    if total == 0:
        pdf.cell(0, 8, "No tasks yet.", ln=True)
    else:
        for task in tasks:
            status = "Done" if task["done"] else "Pending"
            pdf.cell(0, 8, f"- {task['title']} ({status})", ln=True)

    pdf_bytes = bytes(pdf.output())

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=task_summary.pdf"}
    )