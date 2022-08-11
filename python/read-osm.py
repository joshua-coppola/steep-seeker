import pandas as pd
import re
from os.path import exists


def read_osm(filename):
    # Check if file exists
    if not exists(f'data/{filename}'):
        print('No file found')
        return(None)

    # Open file & read each line into an array
    file = open(f'data/{filename}', 'r', encoding='utf8')
    lines = file.readlines()

    for line in lines:
        node_id = None
        node_lat = None
        node_lon = None
        parsed = read_xml_string(line)
        if len(parsed) == 0:
            continue
        if 'node' == parsed['type']:
            try:
                node_id = parsed['id']
                node_lat = parsed['lat']
                node_lon = parsed['lon']
            except:
                continue
        if 'way' == parsed['type']:
            print(parsed)
        if 'nd' == parsed['type']:
            print(parsed)
        if 'tag' == parsed['type']:
            print(parsed)


def read_xml_string(string):
    output = {}
    words = string.split('"')
    for i, word in enumerate(words):
        # skips every other word
        if not '=' in word:
            continue
        # sets up the 'type' header
        if i == 0:
            split_word = word.split()
            output['type'] = re.sub(
                r'[^A-Za-z0-9.\- ]+', ' ', split_word[0]).strip()
            word = split_word[1]
        # adds values & removes weird characters
        output[re.sub(r'[^A-Za-z0-9.\- ]+', ' ', word).strip()
               ] = re.sub(r'[^A-Za-z0-9.\- ]+', ' ', words[i+1]).strip()
    # returns dict
    return output


read_osm('Okemo.osm')
