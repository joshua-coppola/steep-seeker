import db
import maps


def add_resort(name, direction):
    state = db.add_resort(name, direction)
    if state != None:
        maps.create_map(name, state)


#maps.create_map('Alta', 'UT')
add_resort('Okemo', 'w')
