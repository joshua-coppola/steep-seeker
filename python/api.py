import sys
import sqlite3
from flask import Flask, render_template, json, redirect, url_for, request, flash, session, request
from flask_wtf import FlaskForm

from data.secret import secret

sys.path.append('python')

import db as database
import misc


class navigationLink:
    def __init__(self, title, page, to):
        self.title = title
        self.page = page
        self.to = to


class mountainInfo:
    def __init__(self, mountain_id, name, state, statistics, trails, lifts):
        self.mountain_id = mountain_id
        self.name = name
        self.state = state
        self.statistics = statistics
        self.trails = trails
        self.lifts = lifts


app = Flask(__name__, static_url_path='', static_folder='../static', template_folder='../templates')
app.config['SECRET_KEY'] = secret

nav_links = []
nav_links.append(navigationLink("About", "about", "/about"))
nav_links.append(navigationLink("Search", "search", "/search"))
nav_links.append(navigationLink("Rankings", "rankings",
                                "/rankings?sort=difficulty&order=desc&region=usa"))


@app.route("/")
def index():
    return render_template("index.jinja", nav_links=nav_links, active_page="index")


@app.route("/about")
def about():
    return render_template("about.jinja", nav_links=nav_links, active_page="about")

@app.route("/search")
def search():
    # parsing query string for database search
    search_string = ""
    q = request.args.get('q')
    if q and q != "%%":
        q = "%" + q + "%"
        search_string += "q=" + q.replace("%", "") + "&"
    else:
        q = "%%"
    page = request.args.get('page')
    if not page:
        page = 1
    limit = request.args.get('limit')
    if not limit:
        limit = 20
    else:
        search_string += "limit=" + str(limit) + "&"
    diffmin = request.args.get('diffmin')
    if not diffmin:
        diffmin = 0
    else:
        search_string += "diffmin=" + str(diffmin) + "&"
    diffmax = request.args.get('diffmax')
    if not diffmax:
        diffmax = 100
    else:
        search_string += "diffmax=" + str(diffmax) + "&"
    location = request.args.get('location')
    if not location or location == "%%":
        location = "%%"
    else:
        search_string += "location=" + location + "&"
    trailsmin = request.args.get('trailsmin')
    if not trailsmin:
        trailsmin = 0
    else:
        search_string += "trailsmin=" + str(trailsmin) + "&"
    trailsmax = request.args.get('trailsmax')
    if not trailsmax:
        trailsmax = 1000
    else:
        search_string += "trailsmax=" + str(trailsmax) + "&"
    sort = request.args.get('sort')
    if not sort:
        sort = 'name'
    else:
        search_string += "sort=" + sort + "&"
    order = request.args.get('order')
    if not order:
        order = 'asc'
    else:
        search_string += "order=" + order + "&"

    if len(search_string) > 0 and search_string[-1] == "&":
        search_string = search_string[0:-1]
    
    limit = int(limit)
    offset = limit * (int(page) - 1)

    cur, db = database.db_connect()

    if not sort in ['name', 'trail_count', 'lift_count', 'vertical', 'difficulty', 'beginner_friendliness']:
        sort = name

    if not order in ['asc', 'desc']:
        order = 'asc'

    query = f'SELECT name, beginner_friendliness, difficulty, state, trail_count, vertical, mountain_id  FROM Mountains WHERE name LIKE ? AND state LIKE ? AND trail_count BETWEEN ? AND ? AND difficulty BETWEEN ? AND ? ORDER BY {sort} {order} LIMIT ? OFFSET ?'
    params = (q, location, trailsmin, trailsmax, diffmin, diffmax, limit, offset)
    mountains = cur.execute(query,params).fetchall()

    db.close()

    mountains_data = []
    for mountain in mountains:
        name = mountain[0]
        mountains_data.append({
            'name': name,
            'beginner_friendliness': mountain[1],
            'difficulty': mountain[2],
            'state': misc.convert_state_abbrev_to_name(mountain[3]),
            'trail_count': mountain[4],
            'vertical': mountain[5],
            #'map_link': url_for('map', mountain_id=mountain[6]),
            'thumbnail': f'thumbnails/{name}.svg'})

    pages = {}
    if len(mountains) > limit and (len(mountains) * page) < len(mountains):
        urlBase = "/search?page=" + str(page + 1) + "&"
        urlBase += queryParams
        urlQuery = removesuffix(urlBase, '&')
        pages["next"] = urlQuery
    if offset != 0:
        urlBase = "/search?page=" + str(page - 1) + "&"
        urlBase += queryParams
        urlQuery = removesuffix(urlBase, '&')
        pages["prev"] = urlQuery

    return render_template("mountains.jinja", nav_links=nav_links, active_page="search", mountains=mountains_data, pages=pages)
