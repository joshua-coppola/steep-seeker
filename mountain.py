import db

class Mountain:
    def __init__(self, name: str, state: str = None):
        self.mountain_id = None
        self.name = name
        self.state = state
        self.region = None
        self.direction = None
        self.trail_count = None
        self.lift_count = None
        self.vertical = None
        self.difficulty = None
        self.beginner_friendliness = None

        if self.state != None:
            self._sync()

        if self.state == None:
            value = db._add_resort(self.name)
            if value:
                self._sync()

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
        if trail_dict['area'] == 'True':
            self.area = True
        else:
            self.area = False
        if trail_dict['gladed'] == 'True':
            self.gladed = True
        else:
            self.gladed = False
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
        self.name = lift_dict['name']
        self.length = int(float(lift_dict['length']) * 100 / (2.54 * 12))

    def lat(self):
        if self.mountain_id:
            return db._get_lift_points(self.lift_id, 'lat')
        return None

    def lon(self):
        if self.mountain_id:
            return db._get_lift_points(self.lift_id, 'lon')
        return None
