import os
from rich.progress import track

import db
import maps


def add_resort(name):
    state = db.add_resort(name)
    if state != None:
        print('Creating Map')
        maps.create_map(name, state)
        maps.create_thumbnail(name, state)


def bulk_add_resorts():
    for item in os.listdir('data/osm'):
        if item.endswith('.osm'):
            add_resort(item.split('.')[0])


def refresh_resort(name, state):
    return_state = db.refresh_resort(name, state)
    if state == return_state:
        print('Creating Map')
        maps.create_map(name, state)
        maps.create_thumbnail(name, state)


def bulk_refresh_resorts():
    mountains = db.get_mountains()
    for i, mountain in enumerate(mountains):
        print(f'\nResort #{i + 1}/{len(mountains)}')
        print(f'{mountain[0]}\n')
        refresh_resort(mountain[0], mountain[1])


def bulk_create_maps():
    mountains = db.get_mountains()
    for mountain in track(mountains):
        maps.create_map(mountain[0], mountain[1])
        maps.create_thumbnail(mountain[0], mountain[1])


def delete_resort(name, state):
    db.delete_resort(name, state)
    if os.path.exists(f'data/osm/{state}/{name}.osm'):
        os.remove(f'data/osm/{state}/{name}.osm')
    if os.path.exists(f'data/maps/{state}/{name}.svg'):
        os.remove(f'data/maps/{state}/{name}.svg')
    if os.path.exists(f'data/thumbnails/{state}/{name}.svg'):
        os.remove(f'data/thumbnails/{state}/{name}.svg')


def delete_all_resorts():
    mountains = db.get_mountains()
    for mountain in mountains:
        db.delete_resort(mountain[0], mountain[1])


def rotate_map_clockwise(name, state):
    db.rotate_clockwise(name, state)
    maps.create_map(name, state)
    maps.create_thumbnail(name, state)


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


def prune_objects(resort_name, state, prune_id_list, debug_mode=True):
    mountain_id = db.get_mountain_id(resort_name, state)
    for item in prune_id_list:
            db.delete_trail(mountain_id, item)
            db.delete_lift(mountain_id, item)
    maps.create_map(resort_name, state, True, debug_mode)
    maps.create_thumbnail(resort_name, state)


def bulk_update_mountain_stats():
    cur, database = db.db_connect()

    mountains = db.get_mountains()
    for mountain in mountains:
        mountain_id = db.get_mountain_id(mountain[0], mountain[1])
        db.calc_mountain_stats(cur, mountain_id)

    database.commit()
    database.close()


def repl():
    valid = True
    while valid:
        print('\nSelect an action by entering the corresponding number:')
        print('1) Add a resort')
        print('2) Add all resorts that are unprocessed')
        print('3) Refresh a resort')
        print('4) Refresh all resorts')
        print('5) Create new map for a resort')
        print('6) Create new maps for all resorts')
        print('7) Update stats for all resorts')
        print('8) Delete a trail or lift')
        print('9) Delete a resort')
        print('Other value: exit program\n')

        operation = input('Select value: ')
        try:
            operation = int(operation)
        except:
            valid = False
            continue

        if operation > 9 or operation < 1:
            valid = False
            continue

        if operation == 1:
            name = input('\nEnter Resort Name: ')
            add_resort(name)

        if operation == 2:
            bulk_add_resorts()

        if operation == 3:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            refresh_resort(name, state)

        if operation == 4:
            bulk_refresh_resorts()

        if operation == 5:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            maps.create_map(name, state)
            maps.create_thumbnail(name, state)

        if operation == 6:
            bulk_create_maps()

        if operation == 7:
            bulk_update_mountain_stats()

        if operation == 8:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            item_id = input('\nEnter OSM ID')
            mountain_id = db.get_mountain_id(name, state)
            db.delete_trail(mountain_id, item)
            db.delete_lift(mountain_id, item)
            maps.create_map(name, state)
            maps.create_thumbnail(name, state)

        if operation == 9:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            delete_resort(name, state)

        
repl()