import sqlite3
from datetime import datetime

def dict_cursor():
    conn = sqlite3.connect('data/user_db.db')
    conn.row_factory = sqlite3.Row
    return conn


def tuple_cursor():
    conn = sqlite3.connect('data/user_db.db')
    return conn


def reset_db() -> None:
    conn = tuple_cursor()

    with open('user_schema.sql') as f:
        conn.executescript(f.read())


def add_log(ip: str, page_category: str, page_visited: str, parameters: dict() = None):
    if parameters:
        parameters = str(dict(parameters))
        if len(parameters) == 2:
            parameters = None
    else:
        parameters = None
    timestamp = datetime.now()
    
    conn = tuple_cursor()

    query = 'INSERT INTO Log (timestamp, ip, page_category, page_visited, parameters) VALUES (?, ?, ?, ?, ?)'
    params = (timestamp, ip, page_category, page_visited, parameters)

    conn.execute(query, params)
    conn.commit()
    conn.close()