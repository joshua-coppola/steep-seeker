import re
from os.path import exists
from decimal import Decimal

import create_trails


def read_osm(filename):
    # Check if file exists
    if not exists(f'data/{filename}'):
        print('No file found')
        return(None)

    # Open file & read each line into an array
    file = open(f'data/{filename}', 'r', encoding='utf8')
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
                parsed['lat'] = Decimal(parsed['lat'])
                parsed['lon'] = Decimal(parsed['lon'])
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
    trails, lifts = create_trails.process_trails(ways)
    return (trails, lifts)


def read_xml_string(string):
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
