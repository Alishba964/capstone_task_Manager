import os
from dotenv import load_dotenv
from fastapi import FastAPI
import psycopg2
import psycopg2.extras

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

app=FastAPI()

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS tasks(
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


init_db()


@app.get("/")
def root():
    return {"name": "Capstone Task Manager", "status": "skeleton alive"}
@app.get("/tasks")
def get_tasks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks")
    rows = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows




