import db
import maps


def add_resort(name):
    state = db.add_resort(name)
    if state != None:
        maps.create_map(name, state)

#db.delete_resort('Stratton', 'VT')
add_resort('Stratton')
#db.delete_trail(2, 994105796)
#db.delete_lift(2, 31845482)

#maps.create_map('Stratton', 'VT')
