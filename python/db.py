import sqlite3
import os
import csv
from decimal import Decimal
from rich.progress import track

import misc
import read_osm


def db_connect():
    db = sqlite3.connect('data/db.db')
    cur = db.cursor()
    return (cur, db)


def reset_db():
    cur, db = db_connect()

    with open('schema.sql') as f:
        db.executescript(f.read())


def add_trails(cur, mountain_id, trails, lifts):
    for trail in trails:
        cur.execute('INSERT INTO Trails (trail_id, mountain_id, name, area, gladed, official_rating) \
            VALUES ({}, {}, "{}", "{}", "{}", "{}")'.format(trail['id'], mountain_id, trail['name'], trail['area'], trail['gladed'], trail['official_rating']))
        trail['nodes'] = misc.fill_point_gaps(trail['nodes'])
        trail['nodes'] = [{'lat': round(Decimal(x['lat']), 8), 'lon':round(
            Decimal(x['lon']), 8)} for x in trail['nodes']]
        for i, node in enumerate(trail['nodes']):
            cur.execute('INSERT INTO TrailPoints (ind, trail_id, for_display, lat, lon) \
                VALUES ({}, {}, 1, "{}", "{}")'.format(i, trail['id'], str(node['lat']), str(node['lon'])))

    for lift in lifts:
        cur.execute('INSERT INTO Lifts (lift_id, mountain_id, name) \
            VALUES ({}, {}, "{}")'.format(lift['id'], mountain_id, lift['name']))
        lift['nodes'] = misc.fill_point_gaps(lift['nodes'])
        lift['nodes'] = [{'lat': round(Decimal(x['lat']), 8), 'lon':round(
            Decimal(x['lon']), 8)} for x in lift['nodes']]
        for i, node in enumerate(lift['nodes']):
            cur.execute('INSERT INTO LiftPoints (ind, lift_id, lat, lon) \
                VALUES ({}, {}, "{}", "{}")'.format(i, lift['id'], node['lat'], node['lon']))

    # calculate elevation and slope for each point
    print('Processing Trails')
    add_elevation(cur, 'TrailPoints')

    all_incomplete_nodes = cur.execute(
        'SELECT lat, lon, elevation FROM TrailPoints WHERE slope IS NULL').fetchall()

    slope_nodes = misc.get_slope(all_incomplete_nodes)
    for row in slope_nodes:
        cur.execute(
            f'UPDATE TrailPoints SET slope = {row[3]} WHERE lat = "{row[0]}" AND lon =  "{row[1]}"')

    # calculate elevation for each lift point
    print('Processing Lifts')
    # check cache first
    add_elevation(cur, 'LiftPoints')

    # process areas
    trail_ids = cur.execute(
        'SELECT trail_id FROM Trails WHERE area = "True" AND steepest_30m IS NULL').fetchall()

    for trail_id in trail_ids:
        nodes = cur.execute(
            'SELECT lat, lon, elevation FROM TrailPoints WHERE trail_id = ?', (trail_id)).fetchall()

        centerline_nodes = misc.process_area(nodes)
        centerline_nodes = misc.fill_point_gaps(centerline_nodes)
        centerline_nodes = [{'lat': round(Decimal(x['lat']), 8), 'lon':round(
            Decimal(x['lon']), 8)} for x in centerline_nodes]
        for i, node in enumerate(centerline_nodes):
            cur.execute('INSERT INTO TrailPoints (ind, trail_id, for_display, lat, lon) \
                VALUES ({}, {}, 0, "{}", "{}")'.format(i, trail_id[0], node['lat'], node['lon']))

    print('Processing Areas')
    add_elevation(cur, 'TrailPoints')

    all_incomplete_nodes = cur.execute(
        'SELECT lat, lon, elevation FROM TrailPoints WHERE slope IS NULL').fetchall()

    slope_nodes = misc.get_slope(all_incomplete_nodes)
    for row in slope_nodes:
        cur.execute(
            f'UPDATE TrailPoints SET slope = {row[3]} WHERE lat = "{row[0]}" AND lon =  "{row[1]}"')

    # calculate trail pitch, vert, and length
    trails_to_be_rated = cur.execute(
        'SELECT trail_id FROM Trails WHERE steepest_30m IS NULL').fetchall()

    for trail_id in trails_to_be_rated:
        area = cur.execute(
            'SELECT area FROM Trails WHERE trail_id = ?', (trail_id))
        for_display = 1
        if area == 'True':
            for_display = 0
        nodes = cur.execute(
            f'SELECT lat, lon, elevation FROM TrailPoints WHERE trail_id = ? AND for_display = {for_display}', (trail_id)).fetchall()

        pitch_30 = misc.get_steep_pitch(nodes, 30)
        pitch_50 = misc.get_steep_pitch(nodes, 50)
        pitch_100 = misc.get_steep_pitch(nodes, 100)
        pitch_200 = misc.get_steep_pitch(nodes, 200)
        pitch_500 = misc.get_steep_pitch(nodes, 500)
        pitch_1000 = misc.get_steep_pitch(nodes, 1000)
        vert = int(misc.get_vert(nodes))
        length = int(misc.trail_length(nodes))

        cur.execute(f'UPDATE Trails SET steepest_30m = {pitch_30}, steepest_50m = {pitch_50}, \
            steepest_100m = {pitch_100}, steepest_200m = {pitch_200}, \
            steepest_500m = {pitch_500}, steepest_1000m = {pitch_1000}, \
            vertical_drop = {vert}, length = {length} WHERE trail_id = ?', (trail_id))

    # calculate the length of lifts
    lifts_to_be_computed = cur.execute(
        'SELECT lift_id FROM Lifts WHERE length IS NULL').fetchall()

    for lift_id in lifts_to_be_computed:
        nodes = cur.execute(
            'SELECT lat, lon FROM LiftPoints WHERE lift_id = ?', (lift_id)).fetchall()
        length = int(misc.trail_length(nodes))

        cur.execute(
            f'UPDATE Lifts SET length = {length} WHERE lift_id = ?', (lift_id))


def calc_mountain_stats(cur, mountain_id):
    query = 'SELECT elevation FROM TrailPoints NATURAL JOIN (SELECT trail_id FROM Trails WHERE mountain_id = ?)'
    elevations = cur.execute(query, (mountain_id,)).fetchall()

    # only use trails longer than 100m for difficulty calculations
    query = 'SELECT steepest_30m FROM Trails WHERE mountain_id = ? AND length > 100 ORDER BY steepest_30m DESC'
    trail_slopes = cur.execute(query, (mountain_id,)).fetchall()
    difficulty, beginner_friendliness = misc.mountain_rating(trail_slopes)

    query = 'UPDATE Mountains SET vertical = ?, difficulty = ?, beginner_friendliness = ? WHERE mountain_id = ?'
    params = (int(misc.get_vert(elevations)), round(difficulty, 1), round(beginner_friendliness, 1), mountain_id)
    cur.execute(query, params)


# need to automate direction
def add_resort(name):
    cur, db = db_connect()

    state = misc.find_state(f'{name}.osm')

    if state == None:
        return None

    query = 'SELECT COUNT(*) FROM Mountains WHERE name = ? AND state = ?'
    params = (name, state)
    resort_exists = cur.execute(query, params).fetchall()[0][0]

    if resort_exists > 0:
        print('Resort already exists, exiting')
        db.close()
        return None

    trails, lifts = read_osm.read_osm(f'{name}.osm')

    region = misc.assign_region(state)
    trail_count = len(trails)
    lift_count = len(lifts)

    if trail_count == 0:
        print('No trails found, exiting')
        db.close()
        return None

    if lift_count == 0:
        print('No lifts found, exiting')
        db.close()
        return None

    cur.execute(f'INSERT INTO Mountains (name, state, region, trail_count, lift_count) \
        VALUES ("{name}", "{state}", "{region}", {trail_count}, {lift_count})')

    mountain_id = get_mountain_id(name, state, cur)

    add_trails(cur, mountain_id, trails, lifts)

    calc_mountain_stats(cur, mountain_id)

    # set direction
    trail_ids = cur.execute(
        f'SELECT trail_id, area FROM Trails WHERE mountain_id = {mountain_id}').fetchall()

    trail_points = []
    for trail_id in trail_ids:
        if trail_id[1] == 'True':
            trail_points.append(cur.execute(
                f"SELECT lat, lon FROM TrailPoints WHERE trail_id = {trail_id[0]} AND for_display = 0").fetchall())
        if trail_id[1] == 'False':
            trail_points.append(cur.execute(
                f"SELECT lat, lon FROM TrailPoints WHERE trail_id = {trail_id[0]} AND for_display = 1").fetchall())

    direction = misc.find_direction(trail_points)

    cur.execute(
        f'UPDATE Mountains SET direction = "{direction}" WHERE mountain_id = {mountain_id}')

    # move file once processed into the right folder for the state
    if os.path.exists(f'data/osm/{state}'):
        os.rename(f'data/osm/{name}.osm', f'data/osm/{state}/{name}.osm')

    db.commit()
    db.close()

    return state


def refresh_resort(name, state):
    cur, db = db_connect()

    try:
        os.rename(f'data/osm/{state}/{name}.osm', f'data/osm/{name}.osm')
    except:
        if not os.path.exists(f'data/osm/{name}.osm'):
            print('OSM file not found')
            return None

    delete_trails_and_lifts(name, state)
    trails, lifts = read_osm.read_osm(f'{name}.osm')

    trail_count = len(trails)
    lift_count = len(lifts)

    if trail_count == 0:
        print('No trails found, exiting')
        db.close()
        return None

    if lift_count == 0:
        print('No lifts found, exiting')
        db.close()
        return None

    mountain_id = get_mountain_id(name, state)

    query = 'UPDATE Mountains SET trail_count = ?, lift_count = ? WHERE mountain_id = ?'
    params = (trail_count, lift_count, mountain_id)
    cur.execute(query, params)

    add_trails(cur, mountain_id, trails, lifts)

    calc_mountain_stats(cur, mountain_id)

    # move file once processed into the right folder for the state
    if os.path.exists(f'data/osm/{state}'):
        os.rename(f'data/osm/{name}.osm', f'data/osm/{state}/{name}.osm')

    db.commit()
    db.close()

    return state


def delete_resort(name, state):
    cur, db = db_connect()

    delete_trails_and_lifts(name, state)

    query = 'DELETE FROM Mountains WHERE name = ? AND state = ?'
    params = (name, state)
    cur.execute(query, params)

    db.commit()
    db.close()


def delete_trails_and_lifts(name, state):
    cur, db = db_connect()

    # clear out old mountain data without deleting entry in Mountains table
    mountain_id = get_mountain_id(name, state)

    query = 'SELECT trail_id FROM Trails WHERE mountain_id = ?'
    params = (mountain_id,)
    trail_ids = cur.execute(query, params).fetchall()

    query = 'DELETE FROM TrailPoints WHERE trail_id = ?'
    cur.executemany(query, trail_ids)

    query = 'DELETE FROM Trails WHERE mountain_id = ?'
    params = (mountain_id,)
    cur.execute(query, params)

    query = 'SELECT lift_id FROM Lifts WHERE mountain_id = ?'
    params = (mountain_id,)
    lift_ids = cur.execute(query, params).fetchall()

    query = 'DELETE FROM LiftPoints WHERE lift_id = ?'
    cur.executemany(query, lift_ids)

    query = 'DELETE FROM Lifts WHERE mountain_id = ?'
    params = (mountain_id,)
    cur.execute(query, params)

    db.commit()
    db.close()


def delete_trail(mountain_id, trail_id):
    cur, db = db_connect()

    query = 'SELECT COUNT(*) FROM Trails WHERE mountain_id = ? AND trail_id = ?'
    params = (mountain_id, trail_id)
    exists = cur.execute(query, params).fetchall()[0][0]

    if exists != 1:
        return None

    cur.execute(f'DELETE FROM TrailPoints WHERE trail_id = {trail_id}')
    cur.execute(f'DELETE FROM Trails WHERE trail_id = {trail_id}')

    elevations = cur.execute(
        f'SELECT elevation FROM TrailPoints NATURAL JOIN \
        (SELECT trail_id FROM Trails WHERE mountain_id = {mountain_id})').fetchall()

    trail_slopes = cur.execute(
        f'SELECT steepest_30m FROM Trails WHERE mountain_id = {mountain_id} ORDER BY steepest_30m DESC').fetchall()
    difficulty, beginner_friendliness = misc.mountain_rating(trail_slopes)
    trail_count = cur.execute(
        f'SELECT trail_count FROM Mountains WHERE mountain_id = {mountain_id}').fetchall()[0][0]
    cur.execute(
        f'UPDATE Mountains SET vertical = {int(misc.get_vert(elevations))}, difficulty = {round(difficulty, 1)}, \
            beginner_friendliness = {round(beginner_friendliness, 1)}, trail_count = {trail_count - 1} WHERE mountain_id = {mountain_id}')

    db.commit()
    db.close()


def delete_lift(mountain_id, lift_id):
    cur, db = db_connect()

    query = 'SELECT COUNT(*) FROM Lifts WHERE mountain_id = ? AND lift_id = ?'
    params = (mountain_id, lift_id)
    exists = cur.execute(query, params).fetchall()[0][0]

    if exists != 1:
        return None

    cur.execute(f'DELETE FROM LiftPoints WHERE lift_id = {lift_id}')
    cur.execute(f'DELETE FROM Lifts WHERE lift_id = {lift_id}')

    lift_count = cur.execute(
        f'SELECT lift_count FROM Mountains WHERE mountain_id = {mountain_id}').fetchall()[0][0]
    cur.execute(
        f'UPDATE Mountains SET lift_count = {lift_count - 1} WHERE mountain_id = {mountain_id}')

    db.commit()
    db.close()


def fill_cache():
    cur, db = db_connect()

    for item in os.listdir('data/cached'):
        with open(f'data/cached/{item}', mode='r') as csv_file:
            csv_contents = csv.reader(csv_file)
            next(csv_contents)
            for line in csv_contents:
                try:
                    cur.execute(
                        f'INSERT INTO CachedPoints (lat, lon, elevation) VALUES ({line[2]}, {line[3]}, {line[4]})')
                except:
                    count = cur.execute(
                        f'SELECT COUNT(*) FROM CachedPoints WHERE lat = {line[2]} AND lon = {line[3]}').fetchall()[0][0]
                    if count > 0:
                        continue
                    else:
                        return -1
    db.commit()
    db.close()


def get_mountain_id(name, state, cur=None):
    if cur == None:
        cur, db = db_connect()

    query = 'SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?'
    params = (name, state)
    mountain_id = cur.execute(query, params).fetchall()[0][0]

    return mountain_id


def get_mountains():
    cur, db = db_connect()

    mountains = cur.execute('SELECT name, state FROM Mountains').fetchall()

    db.close()
    return(mountains)


def add_elevation(cur, table):
    if table != 'TrailPoints' and table != 'LiftPoints':
        print('Bad value for table name')
        return

    query = f'SELECT lat, lon FROM {table} WHERE elevation IS NULL'
    all_incomplete_nodes = cur.execute(query).fetchall()

    print(
        f'Before cache: {len(all_incomplete_nodes)} missing elevation values')
    all_incomplete_nodes = [(round(Decimal(x[0]), 8), round(
        Decimal(x[1]), 8)) for x in all_incomplete_nodes]
    # check cache first
    adjustment_values = (Decimal('0'), Decimal(
        '.00000001'), Decimal('-.00000001'))
    elevation_nodes = []
    for node in all_incomplete_nodes:
        for adjustment_lat in adjustment_values:
            for adjustment_lon in adjustment_values:
                lat = node[0] + adjustment_lat
                lon = node[1] + adjustment_lon
                elevation = cur.execute(
                    f'SELECT elevation FROM CachedPoints WHERE lat = {lat} AND lon = {lon}').fetchall()
                if len(elevation) > 0:
                    elevation_nodes.append(
                        (str(elevation[0][0]), str(node[0]), str(node[1])))
                    break

    query = f'UPDATE {table} SET elevation = ? WHERE lat = ? AND lon = ?'
    cur.executemany(query, elevation_nodes)

    query = f'SELECT lat, lon FROM {table} WHERE elevation IS NULL'
    all_incomplete_nodes = cur.execute(query).fetchall()

    all_incomplete_nodes = [(round(Decimal(x[0]), 8), round(
        Decimal(x[1]), 8)) for x in all_incomplete_nodes]

    print(f'After cache: {len(all_incomplete_nodes)} missing elevation values')
    uncached_elevation_nodes = misc.get_elevation(all_incomplete_nodes)
    uncached_elevation_nodes = [(str(x[0]), str(x[1]), str(x[2]))
                                for x in uncached_elevation_nodes]

    query = f'UPDATE {table} SET elevation = ? WHERE lat = ? AND lon = ?'
    cur.executemany(query, uncached_elevation_nodes)

    for node in uncached_elevation_nodes:
        try:
            query = 'INSERT INTO CachedPoints (elevation, lat, lon) VALUES (?, ?, ?)'
            cur.execute(query, node)
        except:
            count = cur.execute(
                f'SELECT COUNT(*) FROM CachedPoints WHERE lat = {node[1]} AND lon = {node[2]}').fetchall()[0][0]
            if count > 0:
                continue
            else:
                print('Error encountered when inserting points into CachedPoints table')
                return(-1)


def rotate_clockwise(name, state):
    cur, db = db_connect()

    query = 'SELECT direction FROM Mountains WHERE name = ? AND state = ?'
    params = (name, state)
    current_direction = cur.execute(query, params).fetchall()[0][0]

    new_direction = ''
    if current_direction == 'n':
        new_direction = 'e'
    if current_direction == 'e':
        new_direction = 's'
    if current_direction == 's':
        new_direction = 'w'
    if current_direction == 'w':
        new_direction = 'n'

    query = 'UPDATE Mountains SET direction = ? WHERE name = ? AND state = ?'
    params = (new_direction, name, state)

    cur.execute(query, params)

    db.commit()
    db.close()


def change_state(name, state, new_state):
    cur, db = db_connect()

    query = 'UPDATE Mountains SET state = ? WHERE name = ? AND state = ?'
    params = (new_state, name, state)

    cur.execute(query, params)
    if os.path.exists(f'data/osm/{state}') and os.path.exists(f'data/osm/{new_state}'):
        os.rename(f'data/osm/{state}/{name}.osm',
                  f'data/osm/{new_state}/{name}.osm')

    if os.path.exists(f'static/maps/{state}') and os.path.exists(f'static/maps/{new_state}'):
        os.rename(f'static/maps/{state}/{name}.svg',
                  f'static/maps/{new_state}/{name}.svg')

    if os.path.exists(f'static/thumbnails/{state}') and os.path.exists(f'static/thumbnails/{new_state}'):
        os.rename(f'static/thumbnails/{state}/{name}.svg',
                  f'static/thumbnails/{new_state}/{name}.svg')

    db.commit()
    db.close()


#db = sqlite3.connect('data/db.db')
#cur = db.cursor()

#cur.execute('ALTER TABLE Trails ADD COLUMN steepest_30m REAL')
#cur.execute('CREATE INDEX TrailId ON TrailPoints(trail_id)')
#cur.execute('CREATE INDEX LiftId ON LiftPoints(lift_id)')

# db.commit()
# db.close()
