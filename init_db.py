import sqlite3

conn = sqlite3.connect("resume.db")
with open("schema.sql") as f:
    conn.executescript(f.read())
conn.close()

print("Resume DB initialized")
