import re
from os.path import exists
from decimal import Decimal
from requests.api import get

import _create_trails


def read_osm(filename: str) -> tuple():
    # Check if file exists
    if not exists(f'data/osm/{filename}'):
        print('No file found')
        return None

    # Open file & read each line into an array
    file = open(f'data/osm/{filename}', 'r', encoding='utf8')
    lines = file.readlines()

    nodes = {}
    in_way = False
    ways = []

    # reads through the file one line at a time
    for line in lines:
        parsed = read_xml_string(line)

        if len(parsed) == 0:
            if ' </way>' in line:
                in_way = False
            continue

        # node processing -- nodes always appear before anything else in an OSM file
        if 'node' == parsed['class']:
            try:
                parsed['lat'] = round(Decimal(parsed['lat']), 8)
                parsed['lon'] = round(Decimal(parsed['lon']), 8)
                nodes[parsed['id']] = {key: parsed[key]
                                       for key in ['lat', 'lon']}
            except:
                print(f'Malformed node: {line}')

        # way processing -- converts list of node ids into coordinates
        if 'way' == parsed['class']:
            in_way = True
            ways.append({'id': parsed['id'], 'nodes': [], 'tags': []})
        if in_way:
            # nd = node reference
            if 'nd' == parsed['class']:
                # find the latitude and longitude from the nodes dict
                if parsed['ref'] in nodes:
                    ways[-1]['nodes'].append(nodes[parsed['ref']])
                else:
                    print('Malformed node reference: {} not found'.format(
                        parsed['ref']))
            # creates list of tags for later use
            if 'tag' == parsed['class']:
                ways[-1]['tags'].append({parsed['k']: parsed['v']})
    trails, lifts = _create_trails.process_trails(ways)
    return (trails, lifts)


def read_xml_string(string: str) -> str:
    output = {}
    words = string.split('"')
    for i, word in enumerate(words):
        # skips every other word
        if not '=' in word:
            continue
        # sets up the 'class' header to identify the type of object
        if i == 0:
            split_word = word.split()
            output['class'] = re.sub(
                r"[^'A-Za-z0-9.\- ]+", ' ', split_word[0]).strip()
            word = split_word[1]
        # adds values & removes weird characters
        output[re.sub(r"[^'A-Za-z0-9.\- ]+", ' ', word).strip()
               ] = re.sub(r"[^'A-Za-z0-9.\- ]+", ' ', words[i+1]).strip()
    # returns dict
    return output


def osm_api(bounding_box: str):
    """
    Helper function for fetching OSM files when coordinates are provided. Accepts 
    a comma separated string of min_lon, min_lat, max_lon, max_lat. 

    Ex: '-72.7867,43.3652,-72.6727,43.4469'

    #### Arguments:

    - bounding_box: string of coordinates in the form outlined above

    #### Returns:

    - OSM text blob
    - None in case of failure
    """
    url = f'https://overpass-api.de/api/map?bbox={bounding_box}'
    print('\nFetching OSM file...')
    for i in range(3):
        response = get(url)
        if response.status_code == 200:
            return response.content
        # time out error
        elif response.status_code == 504:
            continue
        else:
            print('OSM API call failed with code:')
            print(response.status_code)
            print(response.content)
            return None
