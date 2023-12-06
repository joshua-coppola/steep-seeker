import sys
import sqlite3
from flask import Flask, render_template, json, redirect, url_for, request, flash, session, request
from flask_wtf import FlaskForm
from flask_sitemapper import Sitemapper
import os
import geojson
from math import sqrt

from data.secret import secret

import db as database
import _misc
from mountain import Mountain, Trail, Lift


class navigationLink:
    def __init__(self, title, page, to):
        self.title = title
        self.page = page
        self.to = to

sitemap = Sitemapper()

app = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = secret

sitemap.init_app(app)

nav_links = []
nav_links.append(navigationLink('About', 'about', '/about'))
nav_links.append(navigationLink('Search', 'search', '/search'))
nav_links.append(navigationLink('Explore', 'explore', '/explore'))
nav_links.append(navigationLink('Mountain Rankings', 'rankings',
                                '/rankings?sort=difficulty&order=desc&region=usa'))
nav_links.append(navigationLink('Trail Rankings', 'trail_rankings', '/trail-rankings?region=usa'))


@sitemap.include()
@app.route('/')
def index():
    return render_template('index.jinja', nav_links=nav_links, active_page='index')


@sitemap.include()
@app.route('/about')
def about():
    return render_template('about.jinja', nav_links=nav_links, active_page='about')


@sitemap.include()
@app.route('/search')
def search():
    # parsing query string for database search
    search_string = ''
    q = request.args.get('q')
    if q and q != '%%':
        q = f'%{q.strip()}%'
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
        try:
            location = _misc.convert_state_name_to_abbrev(location.title().strip())
        except:
            pass
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


@sitemap.include()
@app.route('/rankings')
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
    if not order in ['asc', 'desc']:
        order = 'desc'
    
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


@sitemap.include()
@app.route('/trail-rankings')
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
        sort_by = 'difficulty'
    if not sort_by in ['difficulty','steepest_30m', 'steepest_50m', 'steepest_100m', 'steepest_200m', 'steepest_500m', 'steepest_1000m']:
        sort_by = 'difficulty'
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

@sitemap.include(url_variables=database._get_mountains())
@app.route('/map/<string:state>/<string:name>')
def map(state, name):
    mountain = Mountain(name, state)

    trails = [Trail(trail['trail_id']) for trail in mountain.trails()]
    
    lifts = [Lift(lift['lift_id']) for lift in mountain.lifts()]

    return render_template('map.jinja', nav_links=nav_links, active_page='map', mountain=mountain, trails=trails, lifts=lifts)


@app.route('/data/<string:state>/<string:name>/objects', methods=['GET'])
def mountaindata(state, name):
    mountain = Mountain(name, state)

    jsonContents = {}

    jsonContents['trails'] = [Trail(trail['trail_id']) for trail in mountain.trails()]
    jsonContents['lifts'] = [Lift(lift['lift_id']) for lift in mountain.lifts()]

    jsonstring = json.dumps(jsonContents)
    return jsonstring


@sitemap.include()
@app.route('/explore')
def explore():
    mountains = database.get_mountains()

    geojson = {'type':'FeatureCollection', 'features':[]}

    for mountain_name in mountains:
        mountain = Mountain(*mountain_name)

        feature = {'type':'Feature',
                'properties':{},
                'geometry':{'type':'Point',
                            'coordinates':[]}}
        feature['geometry']['coordinates'] = [mountain.lon,mountain.lat]
        feature['properties']['name'] = mountain.name
        feature['properties']['state'] = mountain.state
        feature['properties']['trail_count'] = mountain.trail_count
        feature['properties']['lift_count'] = mountain.lift_count
        feature['properties']['vertical'] = mountain.vertical
        feature['properties']['difficulty'] = mountain.difficulty
        feature['properties']['beginner_friendliness'] = mountain.beginner_friendliness
        feature['properties']['size'] = mountain.vertical**(1/3) / 20
        href = f'<a href="/map/{mountain.state}/{mountain.name}">{mountain.name}</a>'
        difficulty_color = _misc.trail_color(mountain.difficulty)
        beginner_color = 'gold'
        if mountain.beginner_friendliness > -17:
            beginner_color = 'red'
        if mountain.beginner_friendliness > -6:
            beginner_color = 'black'
        if mountain.beginner_friendliness > 3:
            beginner_color = 'royalblue'
        if mountain.beginner_friendliness > 12:
            beginner_color = 'green'
        

        feature['properties']['popupContent'] = f'<h3>{href}</h3><p>Vertical: {mountain.vertical} ft</p><p>Difficulty: {mountain.difficulty}<span class="icon difficulty-{difficulty_color}"></span></p><p>Beginner Friendliness: {mountain.beginner_friendliness}<span class="icon difficulty-{beginner_color}"></span></p>'
        feature['properties']['icon'] = f'mountain_{difficulty_color}.png'
        geojson['features'].append(feature)
        
    return render_template('explore.jinja', nav_links=nav_links, active_page='explore', geojson=geojson)


@app.route('/interactive-map/<string:state>/<string:name>')
def interactive_map(state, name):
    mountain = Mountain(name, state)

    trails = [Trail(trail['trail_id']) for trail in mountain.trails()]
    
    lifts = [Lift(lift['lift_id']) for lift in mountain.lifts()]
    
    geojson = {'type':'FeatureCollection', 'features':[]}

    for trail in trails:
        geom_type = 'LineString'
        if trail.area:
            geom_type = 'Polygon'
        feature = {'type':'Feature',
                'properties':{},
                'geometry':{'type': geom_type,
                            'coordinates':[]}}
        coords = list(zip(trail.lon(), trail.lat()))
        coords = [list(element) for element in coords]
        if trail.area:
            coords.append(coords[0])
            coords = [coords]
        feature['geometry']['coordinates'] = coords
        popup_content = f'<h3>{trail.name}</h3><p>Rating: {trail.difficulty}<span class="icon difficulty-{_misc.trail_color(trail.difficulty)}"></span></p>'
        popup_content += f'<p>Length: {trail.length} ft</p><p>Vertical Drop: {trail.vertical} ft</p>'
        if trail.steepest_30m:
            popup_content += f'<p>30m Pitch: {trail.steepest_30m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_30m)}"></span>'
        if trail.steepest_50m:
            popup_content += f'<p>50m Pitch: {trail.steepest_50m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_50m)}"></span>'
        if trail.steepest_100m:
            popup_content += f'<p>100m Pitch: {trail.steepest_100m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_100m)}"></span>'
        if trail.steepest_200m:
            popup_content += f'<p>200m Pitch: {trail.steepest_200m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_200m)}"></span>'
        if trail.steepest_500m:
            popup_content += f'<p>500m Pitch: {trail.steepest_500m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_500m)}"></span>'
        if trail.steepest_1000m:
            popup_content += f'<p>1000m Pitch: {trail.steepest_1000m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_1000m)}"></span>'
        feature['properties']['popupContent'] = popup_content
        feature['properties']['color'] = _misc.trail_color(trail.difficulty)
        feature['properties']['gladed'] = str(trail.gladed)

        geojson['features'].append(feature)

    for lift in lifts:
        feature = {'type':'Feature',
                'properties':{},
                'geometry':{'type': 'LineString',
                            'coordinates':[]}}
        coords = list(zip(lift.lon(), lift.lat()))
        coords = [list(element) for element in coords]
        feature['geometry']['coordinates'] = coords
        popup_content = f'<h3>{lift.name}</h3><p>Length: {lift.length} ft</p>'
        feature['properties']['popupContent'] = popup_content
        feature['properties']['color'] = 'grey'

        geojson['features'].append(feature)

    mountain_dict = {'lat': mountain.lat, 'lon': mountain.lon}

    return render_template('interactive_map.jinja', nav_links=nav_links, active_page='map', geojson=geojson, mountain=mountain, trails=trails, lifts=lifts)

    

@app.route('/sitemap.xml')
def site_map():
    return sitemap.generate()