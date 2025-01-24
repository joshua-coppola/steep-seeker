import sys
import sqlite3
from flask import Flask, render_template, json, redirect, url_for, request, flash, session, request, Response
from flask_wtf import FlaskForm
import os
import geojson
from math import sqrt, degrees, atan2

from data.secret import secret

import db as database
import user_db
import _misc
from mountain import Mountain, Trail, Lift


class navigationLink:
    def __init__(self, title, page, to):
        self.title = title
        self.page = page
        self.to = to


app = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = secret

nav_links = []
nav_links.append(navigationLink('About', 'about', '/about'))
nav_links.append(navigationLink('Search', 'search', '/search'))
nav_links.append(navigationLink('Explore Map', 'explore_map', '/explore-map'))
nav_links.append(navigationLink('Mountain Rankings', 'rankings',
                                '/rankings?sort=difficulty&order=desc&region=usa'))
nav_links.append(navigationLink('Trail Rankings', 'trail_rankings', '/trail-rankings?region=usa'))
nav_links.append(navigationLink('Lift Rankings', 'lift_rankings', '/lift-rankings?region=usa'))


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


@app.route('/lift-rankings')
def lift_rankings():
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
        sort_by = 'vertical_rise'
    if not sort_by in ['vertical_rise','length', 'pitch', 'occupancy', 'bubble', 'heated']:
        sort_by = 'vertical_rise'
    search_string += f'sort={sort_by}&'

    if len(search_string) > 0 and search_string[-1] == '&':
        search_string = search_string[0:-1]

    page = int(page)
    limit = int(limit)
    offset = limit * (page - 1)

    conn = database.dict_cursor()

    if sort_by == 'pitch':
        sort_by = 'vertical_rise / Lifts.length'

    if region == 'usa':
        query = f'SELECT lift_id FROM Lifts INNER JOIN Mountains ON Lifts.mountain_id=Mountains.mountain_id WHERE Lifts.name <> "" ORDER BY Lifts.{sort_by} DESC LIMIT ? OFFSET ?'
        lifts = conn.execute(query, (limit, offset)).fetchall()
    else:
        query = f'SELECT lift_id FROM Lifts INNER JOIN Mountains ON Lifts.mountain_id=Mountains.mountain_id WHERE Mountains.region = ? AND Lifts.name <> "" ORDER BY Lifts.{sort_by} DESC LIMIT ? OFFSET ?'
        lifts = conn.execute(query, (region, limit, offset)).fetchall()

    conn.close()

    for i, lift in enumerate(lifts):
        lifts[i] = Lift(lift['lift_id'])

    conn = database.tuple_cursor()

    query = 'SELECT COUNT(*) FROM Lifts'
    total_lift_count = int(conn.execute(query).fetchall()[0][0])

    conn.close()

    pages = {}
    if total_lift_count > limit and (limit * page) < total_lift_count:
        urlBase = f'/lift-rankings?page={page + 1}&{search_string}'
        if len(urlBase) > 0 and urlBase[-1] == '&':
            urlBase = urlBase[0:-1]
        pages['next'] = urlBase
    if offset != 0:
        urlBase = f'/lift-rankings?page={page - 1}&{search_string}'
        if len(urlBase) > 0 and urlBase[-1] == '&':
            urlBase = urlBase[0:-1]
        pages['prev'] = urlBase
    pages['offset'] = offset
    urlBase = f'/lift-rankings?page=1&{search_string}'
    if len(urlBase) > 0 and urlBase[-1] == '&':
        urlBase = urlBase[0:-1]
    pages['first'] = f'/lift-rankings?region={region}&limit={limit}'
    return render_template('lift_rankings.jinja', nav_links=nav_links, active_page='lift_rankings', lifts=lifts, region=region, pages=pages, sort_by=sort_by)

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


@app.route('/explore-map')
def explore_map():
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


        feature['properties']['popupContent'] = f'<h3>{href}</h3>'
        if mountain.season_passes:
            for season_pass in mountain.season_passes:
                feature['properties']['popupContent'] += f'<img src="icons/{season_pass}.png" class="pass-icon"/>'
        feature['properties']['popupContent'] += f'<p>Vertical: {mountain.vertical} ft</p><p>Difficulty: {mountain.difficulty}<span class="icon difficulty-{difficulty_color}"></span></p><p>Beginner Friendliness: {mountain.beginner_friendliness}<span class="icon difficulty-{beginner_color}"></span></p>'
        feature['properties']['icon'] = f'icons/mountain_{difficulty_color}.png'
        geojson['features'].append(feature)

    return render_template('explore_map.jinja', nav_links=nav_links, active_page='explore', geojson=geojson)


@app.route('/interactive-map/<string:state>/<string:name>')
def interactive_map(state, name):
    def get_orientation(lon_points, lat_points):
        midpoint = int(len(lon_points) / 2)
        dx = lon_points[max(midpoint - 5, 0)] - lon_points[min(midpoint + 5, (midpoint * 2) - 1)]
        dy = lat_points[max(midpoint - 5, 0)] - lat_points[min(midpoint + 5, (midpoint * 2) - 1)]
        ang = degrees(atan2(dy, dx))
        orientation = 0
        if abs(ang) < 90 and not trail.area and mountain.direction == 's':
            orientation = 180
        if abs(ang) > 90 and not trail.area and mountain.direction == 'n':
            orientation = 180
        if ang > 0 and not trail.area and mountain.direction == 'w':
            orientation = 180
        if ang < 0 and not trail.area and mountain.direction == 'e':
            orientation = 180

        return orientation

    debug_mode = False
    debug = request.args.get('debug')
    if debug == 'true':
        debug_mode = True

    mountain = Mountain(name, state)

    trails = [Trail(trail['trail_id']) for trail in mountain.trails()]

    lifts = [Lift(lift['lift_id']) for lift in mountain.lifts()]

    geojson = {'type':'FeatureCollection', 'features':[], 'properties':{'summary':'elevation'} }

    for trail in trails:
        geom_type = 'LineString'
        if trail.area:
            geom_type = 'Polygon'
        feature = {'type':'Feature',
                'properties':{},
                'geometry':{'type': geom_type,
                            'coordinates':[]}}
        trail_points = list(zip(trail.lat(), trail.lon(), trail.elevation(round_to_int = True)))
        trail_points = _misc.get_slope(trail_points)
        coords = [[element[1], element[0], element[2], element[3]] for element in trail_points]

        if trail.area:
            coords.append(coords[0])
            coords = [coords]
        feature['geometry']['coordinates'] = coords
        if trail.gladed:
            gladed = '<i class="icon gladed"></i>'
        else:
            gladed = ''
        if trail.ungroomed:
            ungroomed = '<span>&nbsp;&nbsp;</span><i class="icon ungroomed"></i>'
        else:
            ungroomed = ''
        popup_content = f'<h3>{trail.name}{gladed}{ungroomed}</h3>'
        popup_content += f'<p>Rating: {trail.difficulty}<span class="icon difficulty-{_misc.trail_color(trail.difficulty)}"></span></p>'
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
        if debug_mode:
            popup_content += f'<p>Trail ID: {trail.trail_id}</p>'

        feature['properties']['popupContent'] = popup_content
        feature['properties']['label'] = f'{trail.name}'

        lon_points = trail.lon()
        lat_points = trail.lat()

        orientation = get_orientation(lon_points, lat_points)

        feature['properties']['orientation'] = orientation
        feature['properties']['color'] = _misc.trail_color(trail.difficulty)
        feature['properties']['gladed'] = str(trail.gladed)
        feature['properties']['difficulty_modifier'] = trail.difficulty - trail.steepest_30m

        geojson['features'].append(feature)

    whole_resort_modifier = trails[0].difficulty - trails[0].steepest_30m - (trails[0].gladed * 5.5) - (trails[0].ungroomed * 2.5)
    print(whole_resort_modifier)

    for lift in lifts:
        feature = {'type':'Feature',
                'properties':{},
                'geometry':{'type': 'LineString',
                            'coordinates':[]}}

        lift_points = list(zip(lift.lat(), lift.lon(), lift.elevation(round_to_int = True)))
        lift_points = _misc.get_slope(lift_points)
        coords = [[element[1], element[0], element[2], element[3]] for element in lift_points]

        feature['geometry']['coordinates'] = coords
        popup_content = f'<h3>{lift.name}</h3>'
        if lift.occupancy:
            if lift.occupancy <= 4:
                popup_content += '<p>'
                for i in range(lift.occupancy):
                    popup_content += '<span class="icon person"></span>'
                popup_content += '</p>'
            else:
                popup_content += '<p class="occupancy">'
                popup_content += f'{lift.occupancy}<span class="small-spacer"></span><span class="icon person"></span></p>'
        popup_content += f'<p>Length: {lift.length} ft</p>'
        popup_content += f'<p>Vertical Rise: {lift.vertical} ft</p>'
        popup_content += f'<p>Average Pitch: {lift.pitch}°</p>'
        if lift.bubble:
            popup_content += f'<p>&#x2705; Bubble</p>'
        if lift.heated:
            popup_content += f'<p>&#x2705; Heated</p>'
        if debug_mode:
            popup_content += f'<p>Lift ID: {lift.lift_id}</p>'
        feature['properties']['popupContent'] = popup_content
        feature['properties']['label'] = f'{lift.name}'

        lon_points = lift.lon()
        lat_points = lift.lat()

        orientation = get_orientation(lon_points, lat_points)
        feature['properties']['orientation'] = orientation
        feature['properties']['color'] = 'grey'
        feature['properties']['difficulty_modifier'] = whole_resort_modifier

        geojson['features'].append(feature)

    return render_template('interactive_map.jinja', nav_links=nav_links, active_page='map', geojson=geojson, mountain=mountain, trails=trails, lifts=lifts)


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.jinja', nav_links=nav_links)


@app.route('/sitemap.xml')
def site_map():
    xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    footer = '</urlset>'
    url = '<url><loc>https://steepseeker.com/{path}</loc><changefreq>monthly</changefreq><priority>{priority}</priority></url>'
    static_page_list = ['', 'about', 'search', 'explore', 'rankings', 'trail_rankings', 'lift_rankings']
    static_page_priority = [1, .6, .7, .8, .9, .9, .8]
    dynamic_page_list = ['map', 'interactive-map']
    dynamic_page_priority = .3
    for page, priority in zip(static_page_list, static_page_priority):
        xml += url.format(path=page, priority=priority)
    for page in dynamic_page_list:
        for mountain in database.get_mountains():
            xml += url.format(path=page + '/' + mountain[1] + '/' + mountain[0], priority=dynamic_page_priority)
    xml += footer
    return Response(xml, mimetype='text/xml')