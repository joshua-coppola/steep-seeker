import db
import maps


def add_resort(name, direction):
    state = db.add_resort(name, direction)
    if state != None:
        maps.create_map(name, state)


#maps.create_map('Chestnut Mountain', 'IL')
add_resort('Alta', 'n')