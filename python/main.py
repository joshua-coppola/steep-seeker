import os

import db
import maps


def add_resort(name):
    state = db.add_resort(name)
    if state != None:
        maps.create_map(name, state)


def bulk_add_resorts():
    for item in os.listdir('data/osm'):
        if item.endswith('.osm'):
            add_resort(item.split('.')[0])


# db.fill_cache()
bulk_add_resorts()
# add_resort('Bromley')
#db.delete_trail(2, 994105796)
#db.delete_lift(2, 31845482)
#maps.create_map('Stratton', 'VT')
