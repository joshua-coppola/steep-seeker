from decimal import Decimal
import haversine as hs
import time
from requests.api import get
import json
from math import degrees, atan


def assign_region(state: str):
    """
    Takes a 2 letter state code and outputs its region

    #### Arguments:

    - state - US state abbreviations

    #### Returns:

    - region - 'northeast', 'southeast', 'midwest', or 'west'
    """
    northeast = ['ME', 'NH', 'VT', 'NY', 'MA', 'RI', 'CT', 'PA', 'NJ']
    southeast = ['MD', 'DE', 'VA', 'WV', 'KY', 'TN',
                 'NC', 'SC', 'GA', 'FL', 'AL', 'MS', 'LA', 'AR']
    midwest = ['ND', 'SD', 'MN', 'WI', 'MI', 'OH',
               'IN', 'IL', 'IA', 'NE', 'KS', 'MO', 'OK', 'TX']
    west = ['NM', 'AZ', 'CA', 'NV', 'UT', 'CO',
            'WY', 'ID', 'OR', 'WA', 'MT', 'AK', 'HI']

    if len(state.split()) > 1:
        state = state.split()[0]

    if state in northeast:
        return 'northeast'

    if state in southeast:
        return 'southeast'

    if state in midwest:
        return 'midwest'

    if state in west:
        return 'west'
    return 'error'


def fill_point_gaps(nodes):
    max_gap = 15  # 15m between points
    previous_point = nodes[0]

    gaps_exist = True
    loc = 1
    while gaps_exist:
        new_node = {}
        i = loc
        while i < len(nodes):
            point = nodes[i]
            if i == 0:
                previous_point = point
                continue
            dist = hs.haversine((previous_point['lat'], previous_point['lon']), (
                point['lat'], point['lon']), unit=hs.Unit.METERS)

            if dist > max_gap:
                new_node = {'lat': (point['lat'] + previous_point['lat']) / 2,
                            'lon': (point['lon'] + previous_point['lon']) / 2}
                loc = i
                break
            previous_point = point
            i += 1
        if new_node == {}:
            gaps_exist = False
        else:
            nodes.insert(loc, new_node)
    return nodes


def get_elevation(nodes):
    hundred_node_lists = list(divide_chunks(nodes, 100))
    piped_coords_list = []
    elevation = []
    last_called = time.time()
    url = 'https://api.opentopodata.org/v1/ned10m?locations={}'

    for node_list in hundred_node_lists:
        piped_coords = ''
        for node in node_list:
            if piped_coords == '':
                piped_coords = '{},{}'.format(node[0], node[1])
                continue
            piped_coords = piped_coords + \
                '|{},{}'.format(node[0], node[1])
        piped_coords_list.append(piped_coords)

    for item in piped_coords_list:
        if time.time() - last_called < 1:
            time.sleep(1 - (time.time() - last_called))
        response = get(url.format(item))
        last_called = time.time()
        if response.status_code == 200:
            for result in json.loads(response.content)['results']:
                elevation.append(result['elevation'])
        else:
            print('Elevation API call failed on {} with code:'.format(item))
            print(response.status_code)
            print(response.content)
            return None

    if len(nodes) != len(elevation):
        print('Error - Mismatch in number of coordinates vs number of elevation points')

    for i, point_ele in enumerate(elevation):
        nodes[i] = (nodes[i][0], nodes[i][1], point_ele)
    return nodes


def divide_chunks(l, n):

    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_slope(nodes):
    for i, point in enumerate(nodes):
        if i == 0:
            previous_point = point
            nodes[i] = (nodes[i][0], nodes[i][1], nodes[i][2], 0)
            continue
        dist = hs.haversine((previous_point[0], previous_point[1]), (
            point[0], point[1]), unit=hs.Unit.METERS)
        elevation_change = previous_point[2] - point[2]
        previous_point = point
        if elevation_change != 0:
            slope = degrees(atan(elevation_change / dist))
            nodes[i] = (nodes[i][0], nodes[i][1], nodes[i][2], slope)

    # fix weird edge cases where slope is not filled in
    for i, point in enumerate(nodes):
        if len(point) != 4:
            for row in nodes:
                if point[0] in row and point[1] in row and len(row) != 3:
                    nodes[i] = (point[0], point[1], point[2], row[3])
    return nodes
