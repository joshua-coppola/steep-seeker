import sqlite3
import os
import csv
from decimal import Decimal
from datetime import datetime

import _misc
import _read_osm

from classes.states import Region


def db_connect() -> tuple():
    db = sqlite3.connect("data/db.db")
    cur = db.cursor()
    return (cur, db)


def dict_cursor():
    conn = sqlite3.connect("data/db.db")
    conn.row_factory = sqlite3.Row
    return conn


def tuple_cursor():
    conn = sqlite3.connect("data/db.db")
    return conn


def reset_db() -> None:
    cur, db = db_connect()

    with open("schema.sql") as f:
        db.executescript(f.read())


def add_trails(
    cur,
    mountain_id: int,
    trails: list(dict()),
    lifts: list(dict()),
    weather_modifier: float,
) -> None:
    for trail in trails:
        try:
            query = (
                "INSERT INTO Trails (trail_id, mountain_id, name, area, gladed, ungroomed, official_rating) \
                VALUES (?, ?, ?, ?, ?, ?, ?)"
            )
            params = (
                trail["id"],
                mountain_id,
                trail["name"],
                trail["area"],
                trail["gladed"],
                trail["ungroomed"],
                trail["official_rating"],
            )

            cur.execute(query, params)
        except sqlite3.IntegrityError:
            query = "SELECT mountain_id FROM Trails WHERE trail_id = ?"
            params = (trail["id"],)
            conflict_mountain = cur.execute(query, params).fetchone()[0]
            name, trail_id = trail["name"], trail["id"]
            print(
                f"\n{name} {trail_id} is already part of {get_mountain_name(conflict_mountain, cur)}. Skipping Trail."
            )

            query = "SELECT trail_count from Mountains WHERE mountain_id = ?"
            old_trail_count = cur.execute(query, (mountain_id,)).fetchone()[0]

            query = "UPDATE Mountains SET trail_count = ? WHERE mountain_id = ?"
            cur.execute(query, (old_trail_count - 1, mountain_id))
            continue

        trail["nodes"] = _misc.fill_point_gaps(trail["nodes"])
        trail["nodes"] = [
            {"lat": round(Decimal(x["lat"]), 8), "lon": round(Decimal(x["lon"]), 8)}
            for x in trail["nodes"]
        ]
        for i, node in enumerate(trail["nodes"]):
            try:
                query = "INSERT INTO TrailPoints (ind, trail_id, for_display, lat, lon) VALUES (?, ?, ?, ?, ?)"
                params = (i, trail["id"], 1, str(node["lat"]), str(node["lon"]))

                cur.execute(query, params)
            except sqlite3.IntegrityError:
                name, trail_id = trail["name"], trail["id"]
                print(f"{name} {trail_id} {i} is conflicting.")

    for lift in lifts:
        try:
            query = (
                "INSERT INTO Lifts (lift_id, mountain_id, name, occupancy, capacity, duration, detachable, bubble, heated) \
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            params = (
                lift["id"],
                mountain_id,
                lift["name"],
                lift["occupancy"],
                lift["capacity"],
                lift["duration"],
                lift["detachable"],
                lift["bubble"],
                lift["heated"],
            )

            cur.execute(query, params)
        except sqlite3.IntegrityError:
            query = "SELECT mountain_id FROM Lifts WHERE lift_id = ?"
            params = (lift["id"],)
            conflict_mountain = cur.execute(query, params).fetchone()[0]
            name, lift_id = lift["name"], lift["id"]
            print(
                f"\n{name} {lift_id} is already part of {get_mountain_name(conflict_mountain, cur)}. Skipping Lift."
            )

            query = "SELECT lift_count from Mountains WHERE mountain_id = ?"
            old_lift_count = cur.execute(query, (mountain_id,)).fetchone()[0]

            query = "UPDATE Mountains SET lift_count = ? WHERE mountain_id = ?"
            cur.execute(query, (old_lift_count - 1, mountain_id))
            continue
        lift["nodes"] = _misc.fill_point_gaps(lift["nodes"])
        lift["nodes"] = [
            {"lat": round(Decimal(x["lat"]), 8), "lon": round(Decimal(x["lon"]), 8)}
            for x in lift["nodes"]
        ]
        for i, node in enumerate(lift["nodes"]):
            try:
                query = "INSERT INTO LiftPoints (ind, lift_id, lat, lon) VALUES (?, ?, ?, ?)"
                params = (i, lift["id"], str(node["lat"]), str(node["lon"]))

                cur.execute(query, params)
            except sqlite3.IntegrityError:
                name, lift_id = lift["name"], lift["id"]
                print(f"{name} {lift_id} {i} is conflicting.")

    # calculate elevation and slope for each point
    print("Processing Trails")
    add_elevation(cur, "TrailPoints")

    all_incomplete_nodes = cur.execute(
        "SELECT lat, lon, elevation FROM TrailPoints WHERE slope IS NULL"
    ).fetchall()

    slope_nodes = _misc.get_slope(all_incomplete_nodes)
    for row in slope_nodes:
        cur.execute(
            f'UPDATE TrailPoints SET slope = {row[3]} WHERE lat = "{row[0]}" AND lon =  "{row[1]}"'
        )

    # calculate elevation for each lift point
    print("Processing Lifts")
    # check cache first
    add_elevation(cur, "LiftPoints")

    # process areas
    trail_ids = cur.execute(
        "SELECT trail_id FROM Trails WHERE area IS TRUE AND steepest_30m IS NULL"
    ).fetchall()

    for trail_id in trail_ids:
        nodes = cur.execute(
            "SELECT lat, lon, elevation FROM TrailPoints WHERE trail_id = ?", (trail_id)
        ).fetchall()

        centerline_nodes = _misc.process_area(nodes)
        centerline_nodes = _misc.fill_point_gaps(centerline_nodes)
        centerline_nodes = [
            {"lat": round(Decimal(x["lat"]), 8), "lon": round(Decimal(x["lon"]), 8)}
            for x in centerline_nodes
        ]
        for i, node in enumerate(centerline_nodes):
            try:
                query = "INSERT INTO TrailPoints (ind, trail_id, for_display, lat, lon) VALUES (?, ?, ?, ?, ?)"
                params = (i, trail_id[0], 0, str(node["lat"]), str(node["lon"]))

                cur.execute(query, params)
            except sqlite3.IntegrityError:
                name, out_trail_id = trail["name"], trail["id"]
                print(f"\n{name} {out_trail_id} {i} is conflicting.")

        query = "SELECT lat, lon, elevation FROM TrailPoints WHERE trail_id = ? AND for_display = ?"
        params = (trail_id[0], 0)
        nodes = cur.execute(query, params).fetchall()

    print("Processing Areas")
    add_elevation(cur, "TrailPoints")

    all_incomplete_nodes = cur.execute(
        "SELECT lat, lon, elevation FROM TrailPoints WHERE slope IS NULL"
    ).fetchall()

    slope_nodes = _misc.get_slope(all_incomplete_nodes)
    for row in slope_nodes:
        cur.execute(
            f'UPDATE TrailPoints SET slope = {row[3]} WHERE lat = "{row[0]}" AND lon =  "{row[1]}"'
        )

    # calculate trail pitch, vert, and length
    trails_to_be_rated = cur.execute(
        "SELECT trail_id FROM Trails WHERE steepest_30m IS NULL"
    ).fetchall()

    for trail_id in trails_to_be_rated:
        area = cur.execute(
            "SELECT area FROM Trails WHERE trail_id = ?", (trail_id)
        ).fetchone()[0]
        for_display = 1
        if area == 1:
            for_display = 0

        query = "SELECT lat, lon, elevation FROM TrailPoints WHERE trail_id = ? AND for_display = ?"
        params = (trail_id[0], for_display)
        nodes = cur.execute(query, params).fetchall()

        pitch_30 = _misc.get_steep_pitch(nodes, 30)
        pitch_50 = _misc.get_steep_pitch(nodes, 50)
        pitch_100 = _misc.get_steep_pitch(nodes, 100)
        pitch_200 = _misc.get_steep_pitch(nodes, 200)
        pitch_500 = _misc.get_steep_pitch(nodes, 500)
        pitch_1000 = _misc.get_steep_pitch(nodes, 1000)
        vert = int(_misc.get_vert(nodes))
        length = int(_misc.trail_length(nodes))

        difficulty = pitch_30 + weather_modifier

        gladed = cur.execute(
            "SELECT gladed FROM Trails WHERE trail_id = ?", (trail_id)
        ).fetchone()[0]
        if gladed == 1:
            difficulty += 5.5

        ungroomed = cur.execute(
            "SELECT ungroomed FROM Trails WHERE trail_id = ?", (trail_id)
        ).fetchone()[0]
        if ungroomed == 1:
            difficulty += 2.5

        difficulty = round(difficulty, 1)

        cur.execute(
            f"UPDATE Trails SET difficulty = {difficulty}, steepest_30m = {pitch_30}, steepest_50m = {pitch_50}, \
            steepest_100m = {pitch_100}, steepest_200m = {pitch_200}, \
            steepest_500m = {pitch_500}, steepest_1000m = {pitch_1000}, \
            vertical_drop = {vert}, length = {length} WHERE trail_id = ?",
            (trail_id),
        )

    # calculate the length of lifts
    lifts_to_be_computed = cur.execute(
        "SELECT lift_id FROM Lifts WHERE length IS NULL"
    ).fetchall()

    for lift_id in lifts_to_be_computed:
        nodes = cur.execute(
            "SELECT lat, lon, elevation FROM LiftPoints WHERE lift_id = ?", (lift_id)
        ).fetchall()
        length = int(_misc.trail_length(nodes))
        vert = int(_misc.get_vert(nodes))

        cur.execute(
            f"UPDATE Lifts SET length = {length}, vertical_rise = {vert} WHERE lift_id = ?",
            (lift_id),
        )


def calc_mountain_stats(cur, mountain_id: int, mountain_name: str) -> None:
    query = "SELECT elevation FROM TrailPoints NATURAL JOIN (SELECT trail_id FROM Trails WHERE mountain_id = ?)"
    elevations = cur.execute(query, (mountain_id,)).fetchall()

    query = "SELECT lat FROM TrailPoints NATURAL JOIN (SELECT trail_id FROM Trails WHERE mountain_id = ?)"
    lat = cur.execute(query, (mountain_id,)).fetchall()
    lat_fixed = [point[0] for point in lat]

    query = "SELECT lon FROM TrailPoints NATURAL JOIN (SELECT trail_id FROM Trails WHERE mountain_id = ?)"
    lon = cur.execute(query, (mountain_id,)).fetchall()
    lon_fixed = [point[0] for point in lon]

    center_lat = sum(lat_fixed) / len(lat_fixed)
    center_lon = sum(lon_fixed) / len(lon_fixed)

    # only use trails longer than 100m for difficulty calculations
    query = "SELECT difficulty FROM Trails WHERE mountain_id = ? AND length > 100 ORDER BY difficulty DESC"
    trail_difficulty = cur.execute(query, (mountain_id,)).fetchall()
    difficulty, beginner_friendliness = _misc.mountain_rating(trail_difficulty)

    query = "UPDATE Mountains SET vertical = ?, difficulty = ?, beginner_friendliness = ?, lat = ?, lon = ? WHERE mountain_id = ?"
    params = (
        int(_misc.get_vert(elevations)),
        round(difficulty, 1),
        round(beginner_friendliness, 1),
        round(center_lat, 8),
        round(center_lon, 8),
        mountain_id,
    )
    cur.execute(query, params)

    query = "SELECT COUNT(*) FROM Trails WHERE mountain_id = ?"
    params = (mountain_id,)

    manual_trail_count = cur.execute(query, params).fetchone()[0]

    query = "UPDATE Mountains SET trail_count = ? WHERE mountain_id = ?"
    params = (manual_trail_count, mountain_id)

    cur.execute(query, params)


def add_weather_stats(cur, mountain_id: int, mountain_name: str):
    # weather stats, all of them represent season totals
    # the snow value is roughly equal to how much rain it would have been
    filename = f"{mountain_name}.osm"

    lat, lon = _misc.get_center_coordinates(filename)
    weather_dict = _misc.get_weather(lat, lon)

    weather_dict["icy_days"] = float(round(Decimal(weather_dict["icy_days"]), 2))
    weather_dict["snow"] = float(round(Decimal(weather_dict["snow"]), 2))
    weather_dict["rain"] = float(round(Decimal(weather_dict["rain"]), 2))

    query = "UPDATE Mountains SET avg_icy_days = ?, avg_snow = ?, avg_rain = ? WHERE mountain_id = ?"
    params = (
        weather_dict["icy_days"],
        weather_dict["snow"],
        weather_dict["rain"],
        mountain_id,
    )

    cur.execute(query, params)

    return _misc.get_weather_modifier(weather_dict)


def cull_connectors(mountain_id):
    conn = tuple_cursor()

    query = 'SELECT trail_id FROM Trails WHERE name = "" AND length < 100 AND mountain_id = ?'
    trail_ids = conn.execute(query, (mountain_id,)).fetchall()

    query = "SELECT trail_count from Mountains WHERE mountain_id = ?"
    old_trail_count = conn.execute(query, (mountain_id,)).fetchone()[0]

    for trail_id in trail_ids:
        delete_trail(mountain_id, trail_id[0])

    query = "UPDATE Mountains SET trail_count = ? WHERE mountain_id = ?"
    conn.execute(query, (old_trail_count - len(trail_ids), mountain_id))

    conn.commit()
    conn.close()


def _add_resort(name: str) -> str:
    cur, db = db_connect()

    state = _misc.find_state(f"{name}.osm")

    if state is None:
        return None

    query = "SELECT COUNT(*) FROM Mountains WHERE name = ? AND state = ?"
    params = (name, state.value)
    resort_exists = cur.execute(query, params).fetchall()[0][0]

    if resort_exists > 0:
        print("Resort already exists, exiting")
        db.close()
        return None

    trails, lifts = _read_osm.read_osm(f"{name}.osm")

    region = Region.get_region(state)
    trail_count = len(trails)
    lift_count = len(lifts)

    if trail_count == 0:
        print("No trails found, exiting")
        db.close()
        return None

    cur.execute(
        f'INSERT INTO Mountains (name, state, region, trail_count, lift_count) \
        VALUES ("{name}", "{state.value}", "{region.name.lower()}", {trail_count}, {lift_count})'
    )

    mountain_id = get_mountain_id(name, state.value, cur)

    weather_modifier = add_weather_stats(cur, mountain_id, name)

    add_trails(cur, mountain_id, trails, lifts, weather_modifier)

    calc_mountain_stats(cur, mountain_id, name)

    # set direction
    trail_ids = cur.execute(
        f"SELECT trail_id, area FROM Trails WHERE mountain_id = {mountain_id}"
    ).fetchall()

    trail_points = []
    for trail_id in trail_ids:
        if trail_id[1] == 1:
            trail_points.append(
                cur.execute(
                    f"SELECT lat, lon FROM TrailPoints WHERE trail_id = {trail_id[0]} AND for_display = 0"
                ).fetchall()
            )
        if trail_id[1] == 0:
            trail_points.append(
                cur.execute(
                    f"SELECT lat, lon FROM TrailPoints WHERE trail_id = {trail_id[0]} AND for_display = 1"
                ).fetchall()
            )

    direction = _misc.find_direction(trail_points)

    cur.execute(
        f'UPDATE Mountains SET direction = "{direction}" WHERE mountain_id = {mountain_id}'
    )

    # move file once processed into the right folder for the state
    if not os.path.exists(f"data/osm/{state.value}"):
        os.makedirs(f"data/osm/{state.value}")
    os.rename(f"data/osm/{name}.osm", f"data/osm/{state.value}/{name}.osm")

    db.commit()
    db.close()

    cull_connectors(mountain_id)
    _set_last_updated(name, state.value)

    return state.value


def refresh_resort(name: str, state: str, ignore_areas: bool = False) -> str:
    cur, db = db_connect()

    try:
        os.rename(f"data/osm/{state}/{name}.osm", f"data/osm/{name}.osm")
    except:
        if not os.path.exists(f"data/osm/{name}.osm"):
            print("OSM file not found")
            return None

    delete_trails_and_lifts(name, state)
    trails, lifts = _read_osm.read_osm(f"{name}.osm")

    if ignore_areas:
        print("\nRemoving Areas")
        temp_trails = []
        for trail in trails:
            if not trail["area"]:
                temp_trails.append(trail)

        trails = temp_trails

    trail_count = len(trails)
    lift_count = len(lifts)

    if trail_count == 0:
        print("No trails found, exiting")
        db.close()
        return None

    mountain_id = get_mountain_id(name, state)

    query = "UPDATE Mountains SET trail_count = ?, lift_count = ? WHERE mountain_id = ?"
    params = (trail_count, lift_count, mountain_id)
    cur.execute(query, params)

    current_date = [int(x) for x in str(datetime.today().date()).split("-")]

    query = "SELECT last_updated FROM Mountains WHERE mountain_id = ?"
    last_updated_date = [
        int(x) for x in cur.execute(query, (mountain_id,)).fetchone()[0].split("-")
    ]

    need_new_weather = True
    if current_date[0] == last_updated_date[0]:
        # if the year is the same, ski season is at least mostly over, and the data includes the latest season
        if current_date[1] >= 4 and last_updated_date[1] >= 4:
            need_new_weather = False
    if current_date[0] - last_updated_date[0] == 1:
        # if the year is off by 1, but the current season is still in progress, and the data was refreshed last season
        if current_date[1] < 4 and last_updated_date[1] >= 4:
            need_new_weather = False

    if need_new_weather:
        weather_modifier = add_weather_stats(cur, mountain_id, name)
    else:
        query = "SELECT avg_icy_days, avg_snow, avg_rain FROM Mountains WHERE mountain_id = ?"
        weather_data = cur.execute(query, (mountain_id,)).fetchone()
        weather_modifier = _misc.get_weather_modifier(
            {
                "icy_days": weather_data[0],
                "snow": weather_data[1],
                "rain": weather_data[2],
            }
        )

    add_trails(cur, mountain_id, trails, lifts, weather_modifier)

    calc_mountain_stats(cur, mountain_id, name)

    # move file once processed into the right folder for the state
    if not os.path.exists(f"data/osm/{state}"):
        os.makedirs(f"data/osm/{state}")

    # delete old file if there is one
    if os.path.exists(f"data/osm/{state}/{name}.osm"):
        os.remove(f"data/osm/{state}/{name}.osm")
    os.rename(f"data/osm/{name}.osm", f"data/osm/{state}/{name}.osm")

    db.commit()
    db.close()

    cull_connectors(mountain_id)
    _set_last_updated(name, state)

    return state


def delete_resort(name: str, state: str) -> None:
    cur, db = db_connect()

    delete_trails_and_lifts(name, state)

    query = "DELETE FROM Mountains WHERE name = ? AND state = ?"
    params = (name, state)
    cur.execute(query, params)

    db.commit()
    db.close()


def delete_trails_and_lifts(name: str, state: str) -> None:
    cur, db = db_connect()

    # clear out old mountain data without deleting entry in Mountains table
    mountain_id = get_mountain_id(name, state)

    query = "SELECT trail_id FROM Trails WHERE mountain_id = ?"
    params = (mountain_id,)
    trail_ids = cur.execute(query, params).fetchall()

    query = "DELETE FROM TrailPoints WHERE trail_id = ?"
    cur.executemany(query, trail_ids)

    query = "DELETE FROM Trails WHERE mountain_id = ?"
    params = (mountain_id,)
    cur.execute(query, params)

    query = "SELECT lift_id FROM Lifts WHERE mountain_id = ?"
    params = (mountain_id,)
    lift_ids = cur.execute(query, params).fetchall()

    query = "DELETE FROM LiftPoints WHERE lift_id = ?"
    cur.executemany(query, lift_ids)

    query = "DELETE FROM Lifts WHERE mountain_id = ?"
    params = (mountain_id,)
    cur.execute(query, params)

    db.commit()
    db.close()


def delete_trail(mountain_id: int, trail_id: int) -> None:
    cur, db = db_connect()

    query = "SELECT COUNT(*) FROM Trails WHERE mountain_id = ? AND trail_id = ?"
    params = (mountain_id, trail_id)
    exists = cur.execute(query, params).fetchall()[0][0]

    if exists != 1:
        return None

    cur.execute(f"DELETE FROM TrailPoints WHERE trail_id = {trail_id}")
    cur.execute(f"DELETE FROM Trails WHERE trail_id = {trail_id}")

    elevations = cur.execute(
        f"SELECT elevation FROM TrailPoints NATURAL JOIN \
        (SELECT trail_id FROM Trails WHERE mountain_id = {mountain_id})"
    ).fetchall()

    trail_difficulty = cur.execute(
        f"SELECT difficulty FROM Trails WHERE mountain_id = {mountain_id} ORDER BY difficulty DESC"
    ).fetchall()
    difficulty, beginner_friendliness = _misc.mountain_rating(trail_difficulty)
    trail_count = cur.execute(
        f"SELECT trail_count FROM Mountains WHERE mountain_id = {mountain_id}"
    ).fetchall()[0][0]
    cur.execute(
        f"UPDATE Mountains SET vertical = {int(_misc.get_vert(elevations))}, difficulty = {round(difficulty, 1)}, \
            beginner_friendliness = {round(beginner_friendliness, 1)}, trail_count = {trail_count - 1} WHERE mountain_id = {mountain_id}"
    )

    db.commit()
    db.close()


def delete_lift(mountain_id: int, lift_id: int) -> None:
    cur, db = db_connect()

    query = "SELECT COUNT(*) FROM Lifts WHERE mountain_id = ? AND lift_id = ?"
    params = (mountain_id, lift_id)
    exists = cur.execute(query, params).fetchall()[0][0]

    if exists != 1:
        return None

    cur.execute(f"DELETE FROM LiftPoints WHERE lift_id = {lift_id}")
    cur.execute(f"DELETE FROM Lifts WHERE lift_id = {lift_id}")

    lift_count = cur.execute(
        f"SELECT lift_count FROM Mountains WHERE mountain_id = {mountain_id}"
    ).fetchall()[0][0]
    cur.execute(
        f"UPDATE Mountains SET lift_count = {lift_count - 1} WHERE mountain_id = {mountain_id}"
    )

    db.commit()
    db.close()


def fill_cache() -> None:
    cur, db = db_connect()

    for item in os.listdir("data/cached"):
        with open(f"data/cached/{item}", mode="r") as csv_file:
            csv_contents = csv.reader(csv_file)
            next(csv_contents)
            for line in csv_contents:
                try:
                    cur.execute(
                        f"INSERT INTO CachedPoints (lat, lon, elevation) VALUES ({line[2]}, {line[3]}, {line[4]})"
                    )
                except:
                    count = cur.execute(
                        f"SELECT COUNT(*) FROM CachedPoints WHERE lat = {line[2]} AND lon = {line[3]}"
                    ).fetchall()[0][0]
                    if count > 0:
                        continue
                    else:
                        return -1
    db.commit()
    db.close()


def get_mountain_id(name: str, state: str, cur=None) -> int:
    if cur is None:
        cur, db = db_connect()

    query = "SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?"
    params = (name, state)
    mountain_id = cur.execute(query, params).fetchall()[0][0]

    return mountain_id


def get_mountains(state=None) -> list(tuple()):
    cur, db = db_connect()
    if state is None:
        mountains = cur.execute("SELECT name, state FROM Mountains").fetchall()
    else:
        query = "SELECT name, state FROM Mountains WHERE state = ?"
        mountains = cur.execute(query, (state,)).fetchall()

    db.close()
    return mountains


def add_elevation(cur, table: str) -> None:
    if table != "TrailPoints" and table != "LiftPoints":
        print("Bad value for table name")
        return

    query = f"SELECT lat, lon FROM {table} WHERE elevation IS NULL"
    all_incomplete_nodes = cur.execute(query).fetchall()

    print(f"Before cache: {len(all_incomplete_nodes)} missing elevation values")
    all_incomplete_nodes = [
        (round(Decimal(x[0]), 8), round(Decimal(x[1]), 8)) for x in all_incomplete_nodes
    ]
    # check cache first
    adjustment_values = (Decimal("0"), Decimal(".00000001"), Decimal("-.00000001"))
    elevation_nodes = []
    for node in all_incomplete_nodes:
        for adjustment_lat in adjustment_values:
            for adjustment_lon in adjustment_values:
                lat = node[0] + adjustment_lat
                lon = node[1] + adjustment_lon
                elevation = cur.execute(
                    f"SELECT elevation FROM CachedPoints WHERE lat = {lat} AND lon = {lon}"
                ).fetchall()
                if len(elevation) > 0:
                    elevation_nodes.append(
                        (str(elevation[0][0]), str(node[0]), str(node[1]))
                    )
                    break

    query = f"UPDATE {table} SET elevation = ? WHERE lat = ? AND lon = ?"
    cur.executemany(query, elevation_nodes)

    query = f"SELECT lat, lon FROM {table} WHERE elevation IS NULL"
    all_incomplete_nodes = cur.execute(query).fetchall()

    all_incomplete_nodes = [
        (round(Decimal(x[0]), 8), round(Decimal(x[1]), 8)) for x in all_incomplete_nodes
    ]

    print(f"After cache: {len(all_incomplete_nodes)} missing elevation values")
    uncached_elevation_nodes = _misc.get_elevation(all_incomplete_nodes)
    uncached_elevation_nodes = [
        (str(x[0]), str(x[1]), str(x[2])) for x in uncached_elevation_nodes
    ]

    query = f"UPDATE {table} SET elevation = ? WHERE lat = ? AND lon = ?"
    cur.executemany(query, uncached_elevation_nodes)

    for node in uncached_elevation_nodes:
        try:
            query = "INSERT INTO CachedPoints (elevation, lat, lon) VALUES (?, ?, ?)"
            cur.execute(query, node)
        except:
            count = cur.execute(
                f"SELECT COUNT(*) FROM CachedPoints WHERE lat = {node[1]} AND lon = {node[2]}"
            ).fetchall()[0][0]
            if count > 0:
                continue
            else:
                print("Error encountered when inserting points into CachedPoints table")
                return -1


def rotate_clockwise(name: str, state: str) -> None:
    cur, db = db_connect()

    query = "SELECT direction FROM Mountains WHERE name = ? AND state = ?"
    params = (name, state)
    current_direction = cur.execute(query, params).fetchall()[0][0]

    new_direction = ""
    if current_direction == "n":
        new_direction = "e"
    if current_direction == "e":
        new_direction = "s"
    if current_direction == "s":
        new_direction = "w"
    if current_direction == "w":
        new_direction = "n"

    query = "UPDATE Mountains SET direction = ? WHERE name = ? AND state = ?"
    params = (new_direction, name, state)

    cur.execute(query, params)

    db.commit()
    db.close()


def change_state(name: str, state: str, new_state: str) -> None:
    cur, db = db_connect()

    query = "UPDATE Mountains SET state = ? WHERE name = ? AND state = ?"
    params = (new_state, name, state)

    cur.execute(query, params)
    if not os.path.exists(f"data/osm/{new_state}"):
        os.makedirs(f"data/osm/{new_state}")
    if not os.path.exists(f"static/maps/{new_state}"):
        os.makedirs(f"static/maps/{new_state}")
    if not os.path.exists(f"static/thumbnails/{new_state}"):
        os.makedirs(f"static/thumbnails/{new_state}")

    if os.path.exists(f"data/osm/{state}"):
        os.rename(f"data/osm/{state}/{name}.osm", f"data/osm/{new_state}/{name}.osm")

    if os.path.exists(f"static/maps/{state}"):
        os.rename(
            f"static/maps/{state}/{name}.svg", f"static/maps/{new_state}/{name}.svg"
        )

    if os.path.exists(f"static/thumbnails/{state}"):
        os.rename(
            f"static/thumbnails/{state}/{name}.svg",
            f"static/thumbnails/{new_state}/{name}.svg",
        )

    db.commit()
    db.close()


def rename_resort(old_name: str, state: str, new_name: str) -> None:
    cur, db = db_connect()

    query = "UPDATE Mountains SET name = ? WHERE name = ? AND state = ?"
    params = (new_name, old_name, state)

    cur.execute(query, params)
    db.commit()
    db.close()


def change_trail_stats(
    resort_name: str,
    state: str,
    trail_id: int,
    gladed: bool,
    ungroomed: bool,
    area: bool,
) -> None:
    mountain_id = get_mountain_id(resort_name, state)

    cur, db = db_connect()

    difficulty_modifier = 0
    trail_dict = _get_trail_dict(trail_id)

    if trail_dict["gladed"] == 1 or trail_dict["gladed"] == "True":
        difficulty_modifier += 5.5
    if trail_dict["ungroomed"] == 1 or trail_dict["ungroomed"] == "True":
        difficulty_modifier += 2.5

    weather_modifier = (
        trail_dict["difficulty"] - trail_dict["steepest_30m"] - difficulty_modifier
    )

    new_difficulty_modifier = 0
    if gladed:
        new_difficulty_modifier += 5.5
    if ungroomed:
        new_difficulty_modifier += 2.5

    difficulty = new_difficulty_modifier + weather_modifier + trail_dict["steepest_30m"]

    query = "UPDATE Trails SET gladed = ?, ungroomed = ?, area = ?, difficulty = ? WHERE trail_id = ?"
    params = (gladed, ungroomed, area, difficulty, trail_id)

    cur.execute(query, params)

    trail_difficulty = cur.execute(
        f"SELECT difficulty FROM Trails WHERE mountain_id = {mountain_id} ORDER BY difficulty DESC"
    ).fetchall()
    difficulty, beginner_friendliness = _misc.mountain_rating(trail_difficulty)

    cur.execute(
        f"UPDATE Mountains SET difficulty = {round(difficulty, 1)}, \
            beginner_friendliness = {round(beginner_friendliness, 1)} WHERE mountain_id = {mountain_id}"
    )

    db.commit()
    db.close()


def get_mountain_name(mountain_id: int, cur=None) -> str:
    if cur is None:
        cur, db = db_connect()

    query = "SELECT name, state FROM Mountains WHERE mountain_id = ?"
    params = (mountain_id,)
    mountain_name = cur.execute(query, params).fetchone()

    return mountain_name


def bounding_box(name: str, state: str):
    """
    Gets the minimum and maximum latitude and longitude of trails and lifts at a given resort.
    Returns in the order:

    min_lon, min_lat, max_lon, max_lat

    which is the order the Overpass API uses.
    """
    mountain_id = get_mountain_id(name, state)

    conn = tuple_cursor()

    query = "SELECT lat, lon FROM TrailPoints NATURAL JOIN (SELECT trail_id FROM Trails WHERE mountain_id = ?)"
    coords = conn.execute(query, (mountain_id,)).fetchall()

    lat = [row[0] for row in coords]
    lon = [row[1] for row in coords]

    query = "SELECT lat, lon FROM LiftPoints NATURAL JOIN (SELECT lift_id FROM Lifts WHERE mountain_id = ?)"
    coords = conn.execute(query, (mountain_id,)).fetchall()

    lat += [row[0] for row in coords]
    lon += [row[1] for row in coords]

    conn.close()

    return [min(lon), min(lat), max(lon), max(lat)]


def _get_mountain_dict(name: str, state: str) -> dict:
    conn = dict_cursor()

    query = "SELECT * FROM Mountains WHERE name = ? AND state = ?"
    params = (name, state)
    return conn.execute(query, params).fetchone()


def _get_trail_dict(trail_id: int) -> dict:
    conn = dict_cursor()

    query = "SELECT * FROM Trails WHERE trail_id = ?"
    return conn.execute(query, (trail_id,)).fetchone()


def _get_lift_dict(lift_id: int) -> dict:
    conn = dict_cursor()

    query = "SELECT * FROM Lifts WHERE lift_id = ?"
    return conn.execute(query, (lift_id,)).fetchone()


def _get_trails(mountain_id: int) -> list(dict()):
    conn = dict_cursor()

    query = "SELECT * FROM Trails WHERE mountain_id = ? ORDER BY difficulty DESC"
    return conn.execute(query, (mountain_id,)).fetchall()


def _get_lifts(mountain_id: int) -> list(dict()):
    conn = dict_cursor()

    query = "SELECT * FROM Lifts WHERE mountain_id = ? ORDER BY length DESC"
    return conn.execute(query, (mountain_id,)).fetchall()


def _get_trail_points(trail_id: int, column: str, visible: bool) -> list(dict()):
    conn = tuple_cursor()

    if visible:
        for_display = 1
    if not visible:
        for_display = 0
    query = f"SELECT {column} FROM TrailPoints WHERE trail_id = ? AND for_display = ?"
    return_list = conn.execute(query, (trail_id, for_display)).fetchall()

    conn.close()

    return_list = [x[0] for x in return_list]
    return return_list


def _get_lift_points(lift_id: int, column: str) -> list(dict()):
    conn = tuple_cursor()

    query = f"SELECT {column} FROM LiftPoints WHERE lift_id = ?"
    return_list = conn.execute(query, (lift_id,)).fetchall()

    conn.close()

    return_list = [x[0] for x in return_list]
    return return_list


def _get_mountains():
    conn = tuple_cursor()

    query = "SELECT name FROM Mountains"
    names = conn.execute(query).fetchall()

    names = [x[0] for x in names]

    query = "SELECT state FROM Mountains"
    states = conn.execute(query).fetchall()

    states = [y[0] for y in states]

    conn.close()

    return {"state": states, "name": names}


def _set_last_updated(name: str, state: str):
    conn = tuple_cursor()

    date = _misc.last_modified_date(f"data/osm/{state}/{name}.osm")

    query = "UPDATE Mountains SET last_updated = ? WHERE name = ? AND state = ?"
    params = (date, name, state)
    conn.execute(query, params)

    conn.commit()
    conn.close()


def _set_mountain_season_passes(name: str, state: str, passes: str):
    with tuple_cursor() as conn:
        query = "UPDATE Mountains SET season_passes = ? WHERE name = ? AND state = ?"
        params = (passes, name, state)

        conn.execute(query, params)

        conn.commit()


def _set_url(name: str, state: str, url: str):
    with tuple_cursor() as conn:
        query = "UPDATE Mountains SET url = ? WHERE name = ? AND state = ?"
        params = (url, name, state)

        conn.execute(query, params)

        conn.commit()
