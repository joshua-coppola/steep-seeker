import os
from rich.progress import track

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


def bulk_create_maps():
    mountains = db.get_mountains()
    for mountain in track(mountains, description='Creating Maps...'):
        maps.create_map(mountain[0], mountain[1])


#db.rotate_clockwise('Sugar Bowl', 'CA')
#maps.create_map('Sugar Bowl', 'CA')
#db.change_state('Heavenly', 'NV', 'CA')
bulk_add_resorts()
# maps.create_map("Cochran's", 'VT')
# bulk_create_maps()
