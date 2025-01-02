from math import degrees, atan

import db

class Mountain:
    def __init__(self, name: str, state: str = None):
        self.mountain_id = None
        self.name = name
        self.state = state
        self.region = None
        self.direction = None
        self.season_passes = None
        self.trail_count = None
        self.lift_count = None
        self.vertical = None
        self.difficulty = None
        self.beginner_friendliness = None
        self.last_updated = None
        self.bearing = None

        # Allow an empty mountain object if name is passed as None
        if self.name == None:
            return

        if self.state != None:
            self._sync()

        if self.state == None:
            value = db._add_resort(self.name)
            if value:
                self._sync()

        if self.direction == 'n':
            self.bearing = 180
        if self.direction == 'e':
            self.bearing = 270
        if self.direction == 's':
            self.bearing = 0
        if self.direction == 'w':
            self.bearing = 90

    def _sync(self):
        mountain_dict = db._get_mountain_dict(self.name, self.state)

        self.mountain_id = mountain_dict['mountain_id']
        self.region = mountain_dict['region']
        self.direction = mountain_dict['direction']
        self.trail_count = mountain_dict['trail_count']
        self.lift_count = mountain_dict['lift_count']
        self.vertical = int(float(mountain_dict['vertical']) * 100 / (2.54 * 12))
        self.difficulty = mountain_dict['difficulty']
        self.beginner_friendliness = round(30 - mountain_dict['beginner_friendliness'], 1)
        self.lat = mountain_dict['lat']
        self.lon = mountain_dict['lon']
        self.last_updated = mountain_dict['last_updated']
        if mountain_dict['season_passes']:
            self.season_passes = mountain_dict['season_passes'].split(',')
        else:
            self.season_passes = []
        return

    def trails(self):
        if self.mountain_id:
            return db._get_trails(self.mountain_id)
        return None

    def lifts(self):
        if self.mountain_id:
            return db._get_lifts(self.mountain_id)
        return None

class Trail:
    def __init__(self, trail_id: int):
        self.trail_id = trail_id
        
        trail_dict = db._get_trail_dict(self.trail_id)

        self.mountain_id = trail_dict['mountain_id']
        self.name = trail_dict['name']
        if trail_dict['area'] == 1 or trail_dict['area'] == 'True':
            self.area = True
        else:
            self.area = False
        if trail_dict['gladed'] == 1 or trail_dict['gladed'] == 'True':
            self.gladed = True
        else:
            self.gladed = False
        if trail_dict['ungroomed'] == 1 or trail_dict['ungroomed'] == 'True':
            self.ungroomed = True
        else:
            self.ungroomed = False
        self.official_rating = trail_dict['official_rating']
        self.vertical = int(float(trail_dict['vertical_drop']) * 100 / (2.54 * 12))
        self.length = int(float(trail_dict['length']) * 100 / (2.54 * 12))
        self.difficulty = trail_dict['difficulty']
        self.steepest_30m = trail_dict['steepest_30m']
        self.steepest_50m = trail_dict['steepest_50m']
        self.steepest_100m = trail_dict['steepest_100m']
        self.steepest_200m = trail_dict['steepest_200m']
        self.steepest_500m = trail_dict['steepest_500m']
        self.steepest_1000m = trail_dict['steepest_1000m']
        self.resort_name, self.state = db.get_mountain_name(self.mountain_id)

    def lat(self, visible: bool = True):
        if self.mountain_id:
            return db._get_trail_points(self.trail_id, 'lat', visible)
        return None

    def lon(self, visible: bool = True):
        if self.mountain_id:
            return db._get_trail_points(self.trail_id, 'lon', visible)
        return None


class Lift:
    def __init__(self, lift_id: int):
        self.lift_id = lift_id

        lift_dict = db._get_lift_dict(self.lift_id)

        self.mountain_id = lift_dict['mountain_id']
        self.resort_name, self.state = db.get_mountain_name(self.mountain_id)
        self.name = lift_dict['name']
        if lift_dict['length']:
            self.length = int(float(lift_dict['length']) * 100 / (2.54 * 12))
        else:
            self.length = None
        if lift_dict['vertical_rise']:
            self.vertical = int(float(lift_dict['vertical_rise']) * 100 / (2.54 * 12))
        else:
            self.vertical = 0
        if self.length and self.vertical != None:
            self.pitch = round(abs(degrees(atan(self.vertical / self.length))), 1)
        if lift_dict['occupancy']:
            self.occupancy = int(lift_dict['occupancy'])
        else:
            self.occupancy = None
        if lift_dict['capacity']:
            self.capacity = int(lift_dict['capacity'])
        else:
            self.capacity = None
        if lift_dict['duration']:
            self.duration = float(lift_dict['duration'])
        else:
            self.duration = None
        if lift_dict['detachable'] == 1 or lift_dict['detachable'] == 'True':
            self.detachable = True
        else:
            self.detachable = False
        if lift_dict['bubble'] == 1 or lift_dict['bubble'] == 'True':
            self.bubble = True
        else:
            self.bubble = False
        if lift_dict['heated'] == 1 or lift_dict['heated'] == 'True':
            self.heated = True
        else:
            self.heated = False

    def lat(self):
        if self.mountain_id:
            return db._get_lift_points(self.lift_id, 'lat')
        return None

    def lon(self):
        if self.mountain_id:
            return db._get_lift_points(self.lift_id, 'lon')
        return None
