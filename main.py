import os
from rich.progress import track

import db
import maps
import _flask_api
import _read_osm


def add_resort(name: str) -> None:
    state = db._add_resort(name)
    if state != None:
        print('Creating Map')
        maps.create_map(name, state)
        maps.create_thumbnail(name, state)


def bulk_add_resorts() -> None:
    for item in os.listdir('data/osm'):
        if item.endswith('.osm'):
            add_resort(item.split('.')[0])


def refresh_resort(name: str, state: str) -> None:
    return_state = db.refresh_resort(name, state)
    if state == return_state:
        print('Creating Map')
        maps.create_map(name, state)
        maps.create_thumbnail(name, state)


def refresh_resort_from_osm(name: str, state: str, area_padding: float = 0) -> None:
    '''
    Grabs a new OSM file & uses that to refresh the resort. Area padding denotes how much extra space to grab around the
    resort, 1 meaning the bounding box used is double in every dimension, while .5 adds 50% to each dimension. Useful for when
    a resort adds new terrain beyond the previous boundry. An area padding of 0 means that no adjacent land will be selected,
    the safest option for resorts that neighbor each other.
    '''
    bbox = db.bounding_box(name, state)

    lat_adj = (bbox[2] - bbox[0]) * area_padding * .5
    lon_adj = (bbox[3] - bbox[1]) * area_padding * .5

    bbox[0] -= lat_adj
    bbox[1] -= lon_adj
    bbox[2] += lat_adj
    bbox[3] += lon_adj

    bbox_string = f'{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}'
    new_osm_file = _read_osm.osm_api(bbox_string)

    # Todo: make copy of old OSM file with a datestamp, run refresh resort with new file. Add last updated column to mountains table


def bulk_refresh_resorts() -> None:
    mountains = db.get_mountains()
    for i, mountain in enumerate(mountains):
        print(f'\nResort #{i + 1}/{len(mountains)}')
        print(f'{mountain[0]}\n')
        refresh_resort(mountain[0], mountain[1])


def bulk_create_maps() -> None:
    mountains = db.get_mountains()
    for mountain in track(mountains):
        maps.create_map(mountain[0], mountain[1])
        maps.create_thumbnail(mountain[0], mountain[1])


def delete_resort(name: str, state: str) -> None:
    db.delete_resort(name, state)
    if os.path.exists(f'data/osm/{state}/{name}.osm'):
        os.remove(f'data/osm/{state}/{name}.osm')
    if os.path.exists(f'static/maps/{state}/{name}.svg'):
        os.remove(f'static/maps/{state}/{name}.svg')
    if os.path.exists(f'static/thumbnails/{state}/{name}.svg'):
        os.remove(f'static/thumbnails/{state}/{name}.svg')


def rename_resort(old_name: str, state: str, new_name: str) -> None:
    db.rename_resort(old_name, state, new_name)
    if os.path.exists(f'data/osm/{state}/{old_name}.osm'):
        os.rename(f'data/osm/{state}/{old_name}.osm', f'data/osm/{state}/{new_name}.osm' )
    if os.path.exists(f'static/maps/{state}/{old_name}.svg'):
        os.rename(f'static/maps/{state}/{old_name}.svg', f'static/maps/{state}/{new_name}.svg')
    if os.path.exists(f'static/thumbnails/{state}/{old_name}.svg'):
        os.rename(f'static/thumbnails/{state}/{old_name}.svg', f'static/thumbnails/{state}/{new_name}.svg')


def delete_all_resorts() -> None:
    mountains = db.get_mountains()
    for mountain in mountains:
        db.delete_resort(mountain[0], mountain[1])


def rotate_map_clockwise(name: str, state: str) -> None:
    db.rotate_clockwise(name, state)
    maps.create_map(name, state)
    maps.create_thumbnail(name, state)


def move_all_osm_files(source_dir: str) -> None:
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


def prune_objects(resort_name: str, state: str, prune_id_list: list(), debug_mode: bool=True) -> None:
    mountain_id = db.get_mountain_id(resort_name, state)
    for item in prune_id_list:
            db.delete_trail(mountain_id, item)
            db.delete_lift(mountain_id, item)
    maps.create_map(resort_name, state, True, debug_mode)
    maps.create_thumbnail(resort_name, state)


def bulk_update_mountain_stats() -> None:
    cur, database = db.db_connect()

    mountains = db.get_mountains()
    for mountain in mountains:
        mountain_id = db.get_mountain_id(mountain[0], mountain[1])
        db.calc_mountain_stats(cur, mountain_id)

    database.commit()
    database.close()


def repl() -> None:
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
        print('8) Rename a resort')
        print('9) Rotate a map clockwise')
        print('10) Delete a trail or lift')
        print('11) Delete a resort')
        print('12) Start Website')
        print('Other value: exit program\n')

        operation = input('Enter value: ')
        try:
            operation = int(operation)
        except:
            valid = False
            continue

        if operation > 12 or operation < 1:
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
            old_name = input('\nEnter Current Resort Name: ')
            state = input('\nEnter State: ')
            new_name = input('\nEnter New Resort Name: ')
            rename_resort(old_name, state, new_name)
            maps.create_map(new_name, state)

        if operation == 9:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            rotate_map_clockwise(name, state)

        if operation == 10:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            item_id = input('\nEnter OSM ID')
            mountain_id = db.get_mountain_id(name, state)
            db.delete_trail(mountain_id, item)
            db.delete_lift(mountain_id, item)
            maps.create_map(name, state)
            maps.create_thumbnail(name, state)

        if operation == 11:
            name = input('\nEnter Resort Name: ')
            state = input('\nEnter State: ')
            delete_resort(name, state)

        if operation == 12:
            _flask_api.app.run(host='0.0.0.0', port=5000, debug=False)

        
repl()