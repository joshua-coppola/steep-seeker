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


def refresh_resort(name, state):
    return_state = db.refresh_resort(name, state)
    if state == return_state:
        maps.create_map(name, state)


def bulk_refresh_resorts():
    mountains = db.get_mountains()
    for i, mountain in enumerate(mountains):
        print(f'\nResort #{i + 1}/{len(mountains)}')
        print(f'{mountain[0]}\n')
        refresh_resort(mountain[0], mountain[1])


def bulk_create_maps():
    mountains = db.get_mountains()
    for mountain in mountains:
        maps.create_map(mountain[0], mountain[1])


def delete_all_resorts():
    mountains = db.get_mountains()
    for mountain in mountains:
        db.delete_resort(mountain[0], mountain[1])


def rotate_map_clockwise(name, state):
    db.rotate_clockwise(name, state)
    maps.create_map(name, state)


def move_all_osm_files(source_dir):
    # Loop through all subdirectories in the source directory
    for root, dirs, files in os.walk(source_dir):
        # Loop through all files in each subdirectory
        for file_name in files:
            # Create the full file path for the source file
            source_file = os.path.join(root, file_name)
            # Create the full file path for the destination file
            dest_file = os.path.join('data/osm', file_name)
            # Use the os.rename() method to move the file from the source to the destination
            os.rename(source_file, dest_file)


# move_all_osm_files('data/osm/ME')
# bulk_add_resorts()
# bulk_refresh_resorts()
# rotate_map_clockwise('Titcomb', 'ME')
