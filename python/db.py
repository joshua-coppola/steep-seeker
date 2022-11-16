import sqlite3
import os

import misc
import read_osm


def reset_db():
    db = sqlite3.connect('data/db.db')

    with open('schema.sql') as f:
        db.executescript(f.read())


def add_trails(cur, mountain_id, trails, lifts):
    for trail in trails:
        cur.execute('INSERT INTO Trails (trail_id, mountain_id, name, area, gladed, official_rating) \
            VALUES ({}, {}, "{}", "{}", "{}", "{}")'.format(trail['id'], mountain_id, trail['name'], trail['area'], trail['gladed'], trail['official_rating']))
        trail['nodes'] = misc.fill_point_gaps(trail['nodes'])
        for i, node in enumerate(trail['nodes']):
            cur.execute('INSERT INTO TrailPoints (ind, trail_id, for_display, lat, lon) \
                VALUES ({}, {}, 1, "{}", "{}")'.format(i, trail['id'], node['lat'], node['lon']))
    for lift in lifts:
        cur.execute('INSERT INTO Lifts (lift_id, mountain_id, name) \
            VALUES ({}, {}, "{}")'.format(lift['id'], mountain_id, lift['name']))
        trail['nodes'] = misc.fill_point_gaps(lift['nodes'])
        for i, node in enumerate(lift['nodes']):
            cur.execute('INSERT INTO LiftPoints (ind, lift_id, lat, lon) \
                VALUES ({}, {}, "{}", "{}")'.format(i, lift['id'], node['lat'], node['lon']))

    # calculate elevation and slope for each point
    all_incomplete_nodes = cur.execute(
        'SELECT lat, lon FROM TrailPoints WHERE elevation IS NULL').fetchall()

    elevation_values = misc.get_elevation(all_incomplete_nodes)
    slope_nodes = misc.get_slope(elevation_values)
    for row in slope_nodes:
        cur.execute(
            f'UPDATE TrailPoints SET elevation = {row[2]}, slope = {row[3]} WHERE lat = "{row[0]}" AND lon =  "{row[1]}"')

    # calculate trail pitch, vert, and length
    trails_to_be_rated = cur.execute(
        'SELECT trail_id FROM Trails WHERE steepest_50m IS NULL').fetchall()

    for trail_id in trails_to_be_rated:
        nodes = cur.execute(
            'SELECT lat, lon, elevation FROM TrailPoints WHERE trail_id = ?', (trail_id)).fetchall()

        pitch_50 = misc.get_steep_pitch(nodes, 50)
        pitch_100 = misc.get_steep_pitch(nodes, 100)
        pitch_200 = misc.get_steep_pitch(nodes, 200)
        pitch_500 = misc.get_steep_pitch(nodes, 500)
        pitch_1000 = misc.get_steep_pitch(nodes, 1000)
        vert = misc.get_vert(nodes)
        length = misc.trail_length(nodes)

        cur.execute(f'UPDATE Trails SET steepest_50m = {pitch_50}, \
            steepest_100m = "{pitch_100}", steepest_200m = "{pitch_200}", \
            steepest_500m = "{pitch_500}", steepest_1000m = "{pitch_1000}", \
            vertical_drop = {vert}, length = {length} WHERE trail_id = ?', (trail_id))

    # calculate the length of lifts
    lifts_to_be_computed = cur.execute(
        'SELECT lift_id FROM Lifts WHERE length IS NULL').fetchall()

    for lift_id in lifts_to_be_computed:
        nodes = cur.execute(
            'SELECT lat, lon FROM LiftPoints WHERE lift_id = ?', (lift_id)).fetchall()
        length = misc.trail_length(nodes)

        cur.execute(
            f'UPDATE Lifts SET length = {length} WHERE lift_id = ?', (lift_id))


# need to automate direction
def add_resort(name, direction):
    state = misc.find_state(f'{name}.osm')

    if state == None:
        return None

    db = sqlite3.connect('data/db.db')

    cur = db.cursor()

    exists = cur.execute('SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?',
                         (name, state,),).fetchall()

    if len(exists) > 0:
        print('Resort already exists, exiting')
        return

    trails, lifts = read_osm.read_osm(f'{name}.osm')

    region = misc.assign_region(state)
    trail_count = len(trails)
    lift_count = len(lifts)

    if trail_count == 0:
        print('No trails found, exiting')
        db.close()

    # move file once processed into the right folder for the state
    os.rename(f'data/osm/{name}.osm', f'data/osm/{state}/{name}.osm')

    cur.execute(f'INSERT INTO Mountains (name, state, region, direction, trail_count, lift_count) \
        VALUES ("{name}", "{state}", "{region}", "{direction}", {trail_count}, {lift_count})')

    mountain_id = cur.execute('SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?',
                              (name, state,),).fetchone()[0]
    print(cur.execute('SELECT * FROM Mountains').fetchall())

    add_trails(cur, mountain_id, trails, lifts)

    elevations = cur.execute(
        f'SELECT elevation FROM TrailPoints NATURAL JOIN \
        (SELECT trail_id FROM Trails WHERE mountain_id = {mountain_id})').fetchall()

    trail_slopes = cur.execute(
        f'SELECT steepest_50m FROM Trails WHERE mountain_id = {mountain_id} ORDER BY steepest_50m DESC').fetchall()
    difficulty, beginner_friendliness = misc.mountain_rating(trail_slopes)

    cur.execute(
        f'UPDATE Mountains SET vertical = {misc.get_vert(elevations)}, difficulty = {difficulty}, \
            beginner_friendliness = {beginner_friendliness} WHERE mountain_id = {mountain_id}')

    db.commit()
    db.close()


# reset_db()
# add_resort('Alyeska', 'e')

#db = sqlite3.connect('data/db.db')
#cur = db.cursor()

#cur.execute('ALTER TABLE Lifts ADD COLUMN length REAL')

# db.commit()
# db.close()
