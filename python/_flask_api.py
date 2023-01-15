import sys
import sqlite3
from flask import Flask, render_template, json, redirect, url_for, request, flash, session, request
from flask_wtf import FlaskForm
import os

from data.secret import secret

sys.path.append('python')

import db as database
import _misc
from mountain import Mountain, Trail, Lift


class navigationLink:
    def __init__(self, title, page, to):
        self.title = title
        self.page = page
        self.to = to


app = Flask(__name__, static_url_path='', static_folder='../static', template_folder='../templates')
app.config['SECRET_KEY'] = secret

nav_links = []
nav_links.append(navigationLink('About', 'about', '/about'))
nav_links.append(navigationLink('Search', 'search', '/search'))
nav_links.append(navigationLink('Mountain Rankings', 'rankings',
                                '/rankings?sort=difficulty&order=desc&region=usa'))
nav_links.append(navigationLink('Trail Rankings', 'trail_rankings', '/trail-rankings?region=usa'))


@app.route('/')
def index():
    return render_template('index.jinja', nav_links=nav_links, active_page='index')


@app.route('/about')
def about():
    return render_template('about.jinja', nav_links=nav_links, active_page='about')

@app.route('/search')
def search():
    # parsing query string for database search
    search_string = ''
    q = request.args.get('q')
    if q and q != '%%':
        q = f'%{q}%'
        search_string = f'{search_string}q={q.replace("%", "")}&'
    else:
        q = '%%'
    page = request.args.get('page')
    if not page:
        page = 1
    limit = request.args.get('limit')
    if not limit:
        limit = 20
    else:
        search_string = f'{search_string}limit={limit}&'
    diffmin = request.args.get('diffmin')
    if not diffmin:
        diffmin = 0
    else:
        search_string = f'{search_string}diffmin={diffmin}&'
    diffmax = request.args.get('diffmax')
    if not diffmax:
        diffmax = 100
    else:
        search_string = f'{search_string}diffmax={diffmax}&'
    location = request.args.get('location')
    if not location or location == '%%':
        location = '%%'
    else:
        search_string = f'{search_string}location={location}&'
    trailsmin = request.args.get('trailsmin')
    if not trailsmin:
        trailsmin = 0
    else:
        search_string = f'{search_string}trailsmin={trailsmin}&'
    trailsmax = request.args.get('trailsmax')
    if not trailsmax:
        trailsmax = 1000
    else:
        search_string = f'{search_string}trailsmax={trailsmax}&'
    sort = request.args.get('sort')
    if not sort:
        sort = 'name'
    else:
        search_string = f'{search_string}sort={sort}&'
    order = request.args.get('order')
    if not order:
        order = 'asc'
    else:
        search_string = f'{search_string}order={order}&'

    if len(search_string) > 0 and search_string[-1] == '&':
        search_string = search_string[0:-1]
    
    page = int(page)
    limit = int(limit)
    offset = limit * (int(page) - 1)

    if not sort in ['name', 'trail_count', 'lift_count', 'vertical', 'difficulty', 'beginner_friendliness']:
        sort = 'name'

    if not order in ['asc', 'desc']:
        order = 'asc'

    conn = database.dict_cursor()

    query = f'SELECT name, state FROM Mountains WHERE name LIKE ? AND state LIKE ? AND trail_count BETWEEN ? AND ? AND difficulty BETWEEN ? AND ? ORDER BY {sort} {order} LIMIT ? OFFSET ?'
    params = (q, location, trailsmin, trailsmax, diffmin, diffmax, limit, offset)
    mountains = conn.execute(query,params).fetchall()

    conn.close()

    conn = database.tuple_cursor()

    query = 'SELECT COUNT(*) FROM Mountains WHERE name LIKE ? AND state LIKE ? AND trail_count BETWEEN ? AND ? AND difficulty BETWEEN ? AND ?'
    params = (q, location, trailsmin, trailsmax, diffmin, diffmax)
    total_mountain_count = int(conn.execute(query,params).fetchall()[0][0])

    conn.close()

    for i, mountain in enumerate(mountains):
        mountains[i] = Mountain(mountain['name'], mountain['state'])

    pages = {}
    if total_mountain_count > limit and (limit * page) < total_mountain_count:
        urlBase = '/search?page=' + str(page + 1) + '&'
        urlBase += search_string
        if len(urlBase) > 0 and urlBase[-1] == '&':
            urlBase = urlBase[0:-1]
        pages['next'] = urlBase
    if offset != 0:
        urlBase = '/search?page=' + str(page - 1) + '&'
        urlBase += search_string
        if len(urlBase) > 0 and urlBase[-1] == '&':
            urlBase = urlBase[0:-1]
        pages['prev'] = urlBase

    return render_template('search.jinja', nav_links=nav_links, active_page='search', mountains=mountains, pages=pages)


@ app.route('/rankings')
def rankings():
    sort = request.args.get('sort')
    if not sort:
        sort = 'difficulty'
    order = request.args.get('order')
    if not order:
        order = 'desc'
    region = request.args.get('region')
    if not region:
        region = 'usa'
    # converts query string info into SQL
    conn = database.dict_cursor()

    if sort == 'beginner':
        sort_by = 'beginner_friendliness'
    else:
        sort_by = 'difficulty'
    if region == 'usa':
        query = f'SELECT name, state FROM Mountains ORDER BY {sort_by} {order}'
        mountains = conn.execute(query).fetchall()
    else:
        query = f'SELECT name, state FROM Mountains WHERE region = ? ORDER BY {sort_by} {order}'
        mountains = conn.execute(query, (region,)).fetchall()

    for i, mountain in enumerate(mountains):
        mountains[i] = Mountain(mountain['name'], mountain['state'])

    conn.close()
    return render_template('rankings.jinja', nav_links=nav_links, active_page='rankings', mountains=mountains, sort=sort, order=order, region=region)

@ app.route('/trail-rankings')
def trail_rankings():
    search_string = ''
    region = request.args.get('region')
    if not region:
        region = 'usa'
    search_string += f'region={region}&'
    page = request.args.get('page')
    if not page:
        page = 1
    limit = request.args.get('limit')
    if not limit:
        limit = 50
    search_string += f'limit={limit}&'
    sort_by = request.args.get('sort')
    if not sort_by:
        sort_by = 'steepest_30m'
    search_string += f'sort={sort_by}&'

    if len(search_string) > 0 and search_string[-1] == '&':
        search_string = search_string[0:-1]
    
    page = int(page)
    limit = int(limit)
    offset = limit * (page - 1)
    
    conn = database.dict_cursor()

    if region == 'usa':
        query = f'SELECT trail_id FROM Trails INNER JOIN Mountains ON Trails.mountain_id=Mountains.mountain_id WHERE Trails.name <> "" ORDER BY Trails.{sort_by} DESC LIMIT ? OFFSET ?'
        trails = conn.execute(query, (limit, offset)).fetchall()
    else:
        query = f'SELECT trail_id FROM Trails INNER JOIN Mountains ON Trails.mountain_id=Mountains.mountain_id WHERE Mountains.region = ? AND Trails.name <> "" ORDER BY Trails.{sort_by} DESC LIMIT ? OFFSET ?'
        trails = conn.execute(query, (region, limit, offset)).fetchall()

    conn.close()

    for i, trail in enumerate(trails):
        trails[i] = Trail(trail['trail_id'])

    conn = database.tuple_cursor()

    query = 'SELECT COUNT(*) FROM Trails'
    total_trail_count = int(conn.execute(query).fetchall()[0][0])

    conn.close()

    pages = {}
    if total_trail_count > limit and (limit * page) < total_trail_count:
        urlBase = f'/trail-rankings?page={page + 1}&{search_string}'
        if len(urlBase) > 0 and urlBase[-1] == '&':
            urlBase = urlBase[0:-1]
        pages['next'] = urlBase
    if offset != 0:
        urlBase = f'/trail-rankings?page={page - 1}&{search_string}'
        if len(urlBase) > 0 and urlBase[-1] == '&':
            urlBase = urlBase[0:-1]
        pages['prev'] = urlBase
    pages['offset'] = offset
    urlBase = f'/trail-rankings?page=1&{search_string}'
    if len(urlBase) > 0 and urlBase[-1] == '&':
        urlBase = urlBase[0:-1]
    pages['first'] = f'/trail-rankings?region={region}&limit={limit}'
    return render_template('trail_rankings.jinja', nav_links=nav_links, active_page='trail_rankings', trails=trails, region=region, pages=pages, sort_by=sort_by)


@ app.route('/map/<string:state>/<string:name>')
def map(state, name):
    mountain = Mountain(name, state)

    trails = [Trail(trail['trail_id']) for trail in mountain.trails()]
    
    lifts = [Lift(lift['lift_id']) for lift in mountain.lifts()]

    return render_template('map.jinja', nav_links=nav_links, active_page='map', mountain=mountain, trails=trails, lifts=lifts)


@ app.route('/data/<string:state>/<string:name>/objects', methods=['GET'])
def mountaindata(state, name):
    mountain = Mountain(name, state)

    jsonContents = {}

    jsonContents['trails'] = [Trail(trail['trail_id']) for trail in mountain.trails()]
    jsonContents['lifts'] = [Lift(lift['lift_id']) for lift in mountain.lifts()]

    jsonstring = json.dumps(jsonContents)
    return jsonstring
