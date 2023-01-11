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
