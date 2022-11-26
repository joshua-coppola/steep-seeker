import db
import maps


def add_resort(name, direction):
    state = db.add_resort(name, direction)
    if state != None:
        maps.create_map(name, state)


#add_resort('Okemo', 'w')
#db.delete_trail(2, 994105796)
#db.delete_lift(2, 31845480)
#db.delete_lift(2, 31845482)

maps.create_map('Alta', 'UT')
