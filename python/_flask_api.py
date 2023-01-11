import sys
import sqlite3
from flask import Flask, render_template, json, redirect, url_for, request, flash, session, request
from flask_wtf import FlaskForm
import os

from data.secret import secret

sys.path.append('python')

import db as database
import _misc
from mountain import Mountain


class navigationLink:
    def __init__(self, title, page, to):
        self.title = title
        self.page = page
        self.to = to


class mountainInfo:
    def __init__(self, mountain_id, name, state, statistics, trails, lifts, map_link):
        self.mountain_id = mountain_id
        self.name = name
        self.state = state
        self.statistics = statistics
        self.trails = trails
        self.lifts = lifts
        self.map_link = map_link


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
        q = '%' + q + '%'
        search_string += 'q=' + q.replace('%', '') + '&'
    else:
        q = '%%'
    page = request.args.get('page')
    if not page:
        page = 1
    limit = request.args.get('limit')
    if not limit:
        limit = 20
    else:
        search_string += 'limit=' + str(limit) + '&'
    diffmin = request.args.get('diffmin')
    if not diffmin:
        diffmin = 0
    else:
        search_string += 'diffmin=' + str(diffmin) + '&'
    diffmax = request.args.get('diffmax')
    if not diffmax:
        diffmax = 100
    else:
        search_string += 'diffmax=' + str(diffmax) + '&'
    location = request.args.get('location')
    if not location or location == '%%':
        location = '%%'
    else:
        search_string += 'location=' + location + '&'
    trailsmin = request.args.get('trailsmin')
    if not trailsmin:
        trailsmin = 0
    else:
        search_string += 'trailsmin=' + str(trailsmin) + '&'
    trailsmax = request.args.get('trailsmax')
    if not trailsmax:
        trailsmax = 1000
    else:
        search_string += 'trailsmax=' + str(trailsmax) + '&'
    sort = request.args.get('sort')
    if not sort:
        sort = 'name'
    else:
        search_string += 'sort=' + sort + '&'
    order = request.args.get('order')
    if not order:
        order = 'asc'
    else:
        search_string += 'order=' + order + '&'

    if len(search_string) > 0 and search_string[-1] == '&':
        search_string = search_string[0:-1]
    
    page = int(page)
    limit = int(limit)
    offset = limit * (int(page) - 1)

    if not sort in ['name', 'trail_count', 'lift_count', 'vertical', 'difficulty', 'beginner_friendliness']:
        sort = name

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
        query = f'SELECT * FROM Mountains WHERE region = ? ORDER BY {sort_by} {order}'
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

    if len(search_string) > 0 and search_string[-1] == '&':
        search_string = search_string[0:-1]
    
    page = int(page)
    limit = int(limit)
    offset = limit * (page - 1)
    
    cur, db = database.db_connect()

    if region == 'usa':
        query = 'SELECT * FROM Mountains INNER JOIN Trails ON Mountains.mountain_id=Trails.mountain_id WHERE Trails.name <> "" ORDER BY Trails.steepest_30m DESC LIMIT ? OFFSET ?'
        trails = cur.execute(query, (limit, offset)).fetchall()
    else:
        query = 'SELECT * FROM Mountains INNER JOIN Trails ON Mountains.mountain_id=Trails.mountain_id WHERE Mountains.region = ? AND Trails.name <> "" ORDER BY Trails.steepest_30m DESC LIMIT ? OFFSET ?'
        trails = cur.execute(query, (region, limit, offset)).fetchall()
    
    desc = cur.description
    column_names = [col[0] for col in desc]
    trails = [dict(zip(column_names, row)) for row in trails]

    trails_formatted = []
    for trail in trails:
        trail_entry = {
            'name': trail['name'],
            'steepest_30m': trail['steepest_30m'],
            'steepest_50m': trail['steepest_50m'],
            'steepest_100m': trail['steepest_100m'],
            'steepest_200m': trail['steepest_200m'],
            'steepest_500m': trail['steepest_500m'],
            'steepest_1000m': trail['steepest_1000m'],            
            'mountain_name': database.get_mountain_name(trail['mountain_id'], cur)[0],
            'state': trail['state'],
            'map_link': url_for('map', mountain_id=trail['mountain_id'])
        }
        trails_formatted.append(trail_entry)

    query = 'SELECT COUNT(*) FROM Trails'
    total_trail_count = int(cur.execute(query).fetchall()[0][0])

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

    db.close()
    return render_template('trail_rankings.jinja', nav_links=nav_links, active_page='trail_rankings', trails=trails_formatted, region=region, pages=pages)


@ app.route('/map/<int:mountain_id>')
def map(mountain_id):
    conn = database.dict_cursor()

    mountain_row = conn.execute(
        'SELECT name, state FROM Mountains WHERE mountain_id = ?', (mountain_id,)).fetchall()[0]
    if not mountain_row:
        return '404'

    statistics = Mountain(mountain_row['name'], mountain_row['state'])

    trails = conn.execute(
        'SELECT name, gladed, steepest_30m FROM Trails WHERE mountain_id = ? ORDER BY steepest_30m DESC', (mountain_id,)).fetchall()
    labels = ('name', 'difficulty', 'steepest_pitch')
    for i, trail in enumerate(trails):
        if trail['gladed'] == 'False':
            trails[i] = dict(zip(labels, (trail['name'], trail['steepest_30m'], trail['steepest_30m'])))
        if trail['gladed'] == 'True':
            trails[i] = dict(zip(labels, (trail['name'], round(trail['steepest_30m'] + 5.5, 1), trail['steepest_30m'])))
    
    lifts = conn.execute(
        'SELECT name FROM Lifts WHERE mountain_id = ? ORDER BY name ASC', (mountain_id,)).fetchall()

    conn.close()

    map_link = f'../maps/{mountain_row["state"]}/{mountain_row["name"]}.svg'

    mountain = mountainInfo(
        mountain_id, mountain_row['name'], mountain_row['state'], statistics, trails, lifts, map_link)

    return render_template('map.jinja', nav_links=nav_links, active_page='map', mountain=mountain)


@ app.route('/data/<int:mountain_id>/objects', methods=['GET'])
def mountaindata(mountain_id):
    cur, db = database.db_connect()
    trail_rows = cur.execute(
        'SELECT * FROM Trails WHERE mountain_id = ?', (mountain_id,)).fetchall()

    desc = cur.description
    column_names = [col[0] for col in desc]
    trail_rows = [dict(zip(column_names, row)) for row in trail_rows]

    lift_rows = cur.execute(
        'SELECT lift_id, name FROM Lifts WHERE mountain_id = ?', (mountain_id,)).fetchall()

    desc = cur.description
    column_names = [col[0] for col in desc]
    lift_rows = [dict(zip(column_names, row)) for row in lift_rows]

    conn.close()

    if not trail_rows:
        return '404'

    jsonContents = {}
    trails = []
    lifts = []

    for trail in trail_rows:
        if trail['gladed']:
            difficulty = trail['difficulty'] + 5.5
        else:
            difficulty = trail['difficulty']
        trail_entry = {
            'id': trail['trail_id'],
            'name': trail['name'],
            'difficulty': difficulty,
            'length': trail['length'],
            'vertical_drop': trail['vertical_drop'],
            'steepest_pitch': trail['steepest_30m']
        }
        trails.append(trail_entry)

    for lift in lift_rows:
        lift_entry = {
            'id': lift['lift_id'],
            'name': lift['name'],
        }
        lifts.append(lift_entry)

    jsonContents['trails'] = trails
    jsonContents['lifts'] = lifts
    jsonstring = json.dumps(jsonContents)
    return jsonstring
