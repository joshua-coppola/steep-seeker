import sqlite3

db = sqlite3.connect('data/db.db')

with open('schema.sql') as f:
    db.executescript(f.read())

cur = db.cursor()
