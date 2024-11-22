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

    conn.close()


def add_log(ip: str, page_category: str, page_visited: str, parameters: dict() = None, timestamp = None):
    if parameters:
        parameters = str(dict(parameters))
        if len(parameters) == 2:
            parameters = None
    else:
        parameters = None

    if not timestamp:
        timestamp = datetime.now()
    
    conn = tuple_cursor()

    query = 'INSERT INTO Log (timestamp, ip, page_category, page_visited, parameters) VALUES (?, ?, ?, ?, ?)'
    params = (timestamp, ip, page_category, page_visited, parameters)

    conn.execute(query, params)
    conn.commit()
    conn.close()


def bulk_add_log(tuple_list: list(tuple())):
    '''
    Takes in a list of tuples and uses executemany to insert all rows at once.
    The tuples should each contain:
        - timestamp - datetime
        - ip - string
        - page_category - string
        - page_visited - string
        - parameters - str(dict)
    '''
    with tuple_cursor() as conn:
        query = 'INSERT INTO Log (timestamp, ip, page_category, page_visited, parameters) VALUES (?, ?, ?, ?, ?)'

        conn.executemany(query, tuple_list)
        conn.commit()
