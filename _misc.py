import matplotlib.pyplot as plt
from decimal import Decimal
import haversine as hs
import time
from requests.api import get
import json
from math import degrees, atan, atan2
from os.path import exists
from rich.progress import track
import os
from datetime import datetime


def get_center_coordinates(filename: str):
    # Check if file exists
    print(f'\n{filename}\n')
    if not exists(f'data/osm/{filename}'):
        print('No file found')
        return None

    # Open file & read each line into an array
    file = open(f'data/osm/{filename}', 'r', encoding='utf8')
    lines = file.readlines()

    loc = None
    for line in lines:
        if '<bounds' in line:
            loc = line

    if loc == None:
        print('Malformed OSM file. No bounds defined.')
        return None

    line = loc.split('"')
    minlat = Decimal(line[1])
    minlon = Decimal(line[3])
    maxlat = Decimal(line[5])
    maxlon = Decimal(line[7])

    lat = (maxlat + minlat) / 2
    lon = (maxlon + minlon) / 2

    return(lat, lon)


def find_state(filename: str) -> str:
    lat, lon = get_center_coordinates(filename)

    # Uses Open Street Maps Nominatim API to determine which state the resort is in
    url = f'https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}'

    headers = {'User-Agent': 'steepseeker'}


    response = get(url, headers = headers)
    if response.status_code == 200:
        address = json.loads(response.content)['address']
        if address['country_code'] != 'us':
            print('Resort not located in United States. Unsupported region detected.')
            override = input('Continue anyway? Y/N: ')
            if override.lower() == 'y':
                return address['ISO3166-2-lvl4'].split('-')[1]
            return None
        # if location is in USA, return state abbreviation
        return address['ISO3166-2-lvl4'].split('-')[1]
    else:
        print('State API call failed with code:')
        print(response.status_code)
        print(response.content)
        return None


def assign_region(state: str) -> str:
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
    return None


def convert_state_abbrev_to_name(state_abbrev: str) -> str:
    # Define a dictionary that maps state abbreviations to state names
    state_abbrevs_to_names = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
        "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
        "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
        "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
        "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
    }
    return state_abbrevs_to_names[state_abbrev]


def convert_state_name_to_abbrev(state_name):
    # Define a dictionary that maps state names to state abbreviations
    state_names_to_abbrevs = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
        "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
        "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
        "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
        "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
        "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
        "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
        "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
        "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
        "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
    }
    return state_names_to_abbrevs[state_name]


def fill_point_gaps(nodes: list(dict())) -> list(dict()):
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


def get_elevation(nodes: list(tuple())) -> list(tuple()):
    if len(nodes) == 0:
        return []
    hundred_node_lists = list(divide_chunks(nodes, 100))
    piped_coords_list = []
    elevation = []
    last_called = time.time()
    url = 'https://api.opentopodata.org/v1/ned10m?locations={}'
    # global elevation data
    # url = 'https://api.opentopodata.org/v1/mapzen?locations={}'

    for node_list in hundred_node_lists:
        piped_coords = ''
        for node in node_list:
            if piped_coords == '':
                piped_coords = '{},{}'.format(node[0], node[1])
                continue
            piped_coords = piped_coords + \
                '|{},{}'.format(node[0], node[1])
        piped_coords_list.append(piped_coords)

    for item in track(piped_coords_list):
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
        nodes[i] = (point_ele, nodes[i][0], nodes[i][1])
    return nodes


def divide_chunks(l: list, n: int) -> list:

    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_slope(nodes: list(tuple())) -> list(tuple()):
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
            slope = abs(degrees(atan(elevation_change / dist)))
            nodes[i] = (nodes[i][0], nodes[i][1], nodes[i][2], slope)
        else:
            nodes[i] = (nodes[i][0], nodes[i][1], nodes[i][2], 0)

    return nodes


def trail_length(nodes: list(tuple())) -> float:
    previous_point = None
    cumulative_dist = 0

    for i, point in enumerate(nodes):
        if i == 0:
            previous_point = point
            continue
        dist = hs.haversine((previous_point[0], previous_point[1]), (
            point[0], point[1]), unit=hs.Unit.METERS)
        cumulative_dist += dist
        previous_point = point

    return cumulative_dist


def get_steep_pitch(nodes: list(tuple()), length: float) -> float:
    previous_point = None
    max_pitch = -90

    for loc, node in enumerate(nodes):
        i = loc + 1
        cumulative_dist = 0
        while i < len(nodes):
            point = nodes[i]
            previous_point = nodes[i-1]
            i += 1
            if i == 1:
                continue
            dist = hs.haversine((previous_point[0], previous_point[1]), (
                point[0], point[1]), unit=hs.Unit.METERS)
            cumulative_dist += dist
            previous_point = point

            if cumulative_dist >= length:
                elevation_change = nodes[loc][2] - point[2]
                slope = None
                if elevation_change != 0:
                    slope = abs(
                        degrees(atan(elevation_change / cumulative_dist)))
                    if slope < 0:
                        print(slope)
                else:
                    slope = 0
                if slope > max_pitch:
                    max_pitch = slope
                break

    if max_pitch == -90:
        # find difficulty of whole trail if the length desired is short anyway
        if length <= 30:
            elevation_change = nodes[-1][2] - nodes[0][2]
            if elevation_change != 0:
                max_pitch = abs(degrees(
                    atan(elevation_change / trail_length(nodes))))
            else:
                max_pitch = 0
        else:
            return 'NULL'
    return round(max_pitch, 1)


def get_vert(nodes: list(tuple())) -> float:
    max_ele = 0
    min_ele = 10000
    for point in nodes:
        if point[-1] > max_ele:
            max_ele = point[-1]
        if point[-1] < min_ele:
            min_ele = point[-1]
    return max_ele - min_ele


def mountain_rating(nodes: list()) -> tuple:
    divisor = 30
    if len(nodes) < 30:
        divisor = len(nodes)

    small_divisor = 5
    if divisor < small_divisor:
        small_divisor = divisor

    for i, node in enumerate(nodes):
        nodes[i] = node[0]

    difficulty = ((sum(nodes[0:divisor])/divisor)
                  * .2) + ((sum(nodes[0:5])/small_divisor) * .8)

    beginner_friendliness = ((sum(nodes[-divisor:])/divisor)
                             * .2) + ((sum(nodes[-5:])/small_divisor) * .8)
    return(difficulty, beginner_friendliness)


def trail_color(difficulty: float) -> str:
    # 0-18 degrees: green
    if difficulty < 18:
        return 'green'
    # 18-27 degrees: blue
    if difficulty < 27:
        return 'royalblue'
    # 27-36 degrees: black
    if difficulty < 36:
        return 'black'
    # 36-47 degrees: red
    elif difficulty < 47:
        return 'red'
    # >47 degrees: yellow
    else:
        return 'gold'


def find_corrected_center(center_lat: float, center_lon: float, nodes: list(tuple()), north_south: bool) -> tuple():
    if north_south:
        # check lon
        dist = []
        for i, node in enumerate(nodes):
            dist.append((abs(node[0] - center_lat), i))
        dist = sorted(dist)
        closest_index = [i[1] for i in dist[:6]]
        closest_points = [nodes[j] for j in closest_index]
    else:
        # check lat
        dist = []
        for i, node in enumerate(nodes):
            dist.append((abs(node[1] - center_lon), i))
        dist = sorted(dist)
        closest_index = [i[1] for i in dist[:6]]
        closest_points = [nodes[j] for j in closest_index]

    new_center_lat = sum([x[0] for x in closest_points]) / len(closest_points)
    new_center_lon = sum([y[1] for y in closest_points]) / len(closest_points)

    return (new_center_lat, new_center_lon)


def process_area(nodes: list(tuple())) -> list(tuple()):
    max_elevation = (0, 0)
    min_elevation = (10000, 0)

    for i, point in enumerate(nodes):
        if point[2] > max_elevation[0]:
            max_elevation = (point[2], i)
        if point[2] < min_elevation[0]:
            min_elevation = (point[2], i)
    center_lat = sum([x[0] for x in nodes]) / len(nodes)
    center_lon = sum([y[1] for y in nodes]) / len(nodes)

    dx = nodes[max_elevation[1]][0] - nodes[min_elevation[1]][0]
    dy = nodes[max_elevation[1]][1] - nodes[min_elevation[1]][1]

    angle = degrees(atan2(dy, dx))
    north_south = False
    if abs(angle) < 45 or abs(angle) > 135:
        north_south = True

    new_center_lat, new_center_lon = find_corrected_center(
        center_lat, center_lon, nodes, north_south)

    sub_region1 = []
    sub_region2 = []
    for i, node in enumerate(nodes):
        if north_south:
            if node[0] > new_center_lat:
                sub_region1.append(node)
            else:
                sub_region2.append(node)
        if not north_south:
            if node[1] > new_center_lon:
                sub_region1.append(node)
            else:
                sub_region2.append(node)
    center_lat_1 = sum([x[0] for x in sub_region1]) / len(sub_region1)
    center_lon_1 = sum([y[1] for y in sub_region1]) / len(sub_region1)
    center_lat_2 = sum([x[0] for x in sub_region2]) / len(sub_region2)
    center_lon_2 = sum([y[1] for y in sub_region2]) / len(sub_region2)

    plt.scatter(center_lat_1, center_lon_1)
    plt.scatter(center_lat_2, center_lon_2)

    new_center_lat_1, new_center_lon_1 = find_corrected_center(
        center_lat_1, center_lon_1, sub_region1, north_south)

    new_center_lat_2, new_center_lon_2 = find_corrected_center(
        center_lat_2, center_lon_2, sub_region2, north_south)

    plt.scatter(new_center_lat_1, new_center_lon_1)
    plt.scatter(new_center_lat_2, new_center_lon_2)

    sub_region1_ele = [x[2] for x in sub_region1]

    new_nodes = []
    new_node = {'lat': nodes[max_elevation[1]][0],
                'lon': nodes[max_elevation[1]][1]}
    new_nodes.append(new_node)
    if max_elevation[0] in sub_region1_ele:
        new_node = {'lat': new_center_lat_1,
                    'lon': new_center_lon_1}
        new_nodes.append(new_node)
    else:
        new_node = {'lat': new_center_lat_2,
                    'lon': new_center_lon_2}
        new_nodes.append(new_node)
    new_node = {'lat': new_center_lat,
                'lon': new_center_lon}
    new_nodes.append(new_node)
    if max_elevation[0] in sub_region1_ele:
        new_node = {'lat': new_center_lat_2,
                    'lon': new_center_lon_2}
        new_nodes.append(new_node)
    else:
        new_node = {'lat': new_center_lat_1,
                    'lon': new_center_lon_1}
        new_nodes.append(new_node)
    new_node = {'lat': nodes[min_elevation[1]][0],
                'lon': nodes[min_elevation[1]][1]}
    new_nodes.append(new_node)

    return new_nodes


def find_direction(trail_points: list(tuple())) -> str:
    heading = []
    for trail in trail_points:
        dx = trail[0][0] - trail[-1][0]
        dy = trail[0][1] - trail[-1][1]

        heading.append(degrees(atan2(dy, dx)))

    avg_heading = sum(heading) / len(heading)
    direction = []
    for trail_heading in heading:
        if abs(trail_heading) < 45:
            direction.append('n')
            continue
        if abs(trail_heading) > 135:
            direction.append('s')
            continue
        if trail_heading > 0:
            direction.append('e')
            continue
        if trail_heading < 0:
            direction.append('w')
            continue

    if abs(avg_heading) < 45:
        return('n')
    if abs(avg_heading) > 135:
        return('s')
    if avg_heading > 0:
        return('e')
    if avg_heading < 0:
        return('w')


def get_weather(lat: float, lon: float):
    # Uses Open Metro's Historical Weather API to get typical conditions
    # Uses 5 seasons worth of data
    start_date = '2018-11-30'
    end_date = '2023-04-01'
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&models=best_match&daily=weathercode,temperature_2m_max,temperature_2m_min,rain_sum,snowfall_sum&timezone=America%2FNew_York&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch"

    response = get(url)
    if response.status_code == 200:
        data = json.loads(response.content)['daily']
        shaped_data = []
        for i, value in enumerate(data['time']):
            row = {}
            for key in data.keys():
                row[key] = data[key][i]
            shaped_data.append(row)
        return(process_weather(shaped_data))
    elif response.status_code == 429:
        if 'Daily API request limit exceeded. Please try again tomorrow.' in str(response.content):
            raise ValueError('Daily API request limit exceeded. Please try again tomorrow.')
        print('Too Many Weather API requests, waiting 1 minute before resuming')
        time.sleep(60)
        return(get_weather(lat, lon))
    else:
        raise ValueError(f'Weather API call failed with code: {response.status_code} \n{response.content}')
        


def process_weather(weather_list: list):
    winter_list = []
    for row in weather_list:
        date = row['time'].split('-')
        # only include dates from Dec - March
        if int(date[1]) in [1,2,3,12]:
            invalid = False
            for value in row.keys():
                if row[value] == None:
                    invalid = True
            if invalid == True:
                continue
            winter_list.append(row)

    freeze_thaw = 0
    for row in winter_list:
        if float(row['temperature_2m_max']) > 34 and float(row['temperature_2m_min'] < 32):
            freeze_thaw += 1

    rain_total = sum([x['rain_sum'] for x in winter_list])
    snow_total = sum([x['snowfall_sum'] for x in winter_list])

    return {'icy_days': freeze_thaw / 5, 'rain': rain_total / 5, 'snow': snow_total / 5}


def get_weather_modifier(weather_dict: dict):
    '''
    A resort can have a modifier of between 0-6 degrees based off how it's weather compares 
    to other resorts. Each weather value contributes up to 2 degrees of difficulty.
    A resort that is 2 SD harder than the mean for a given metric gets the full two points.

    The statistical values for each metric are as follows (Updated 2023-12-28):
    Metric       | Mean              | Standard Deviation
    avg_icy_days | 40.13571428571428 | 18.81610659373872     
    avg_snow     | 79.67810714285716 | 61.38204737243106     
    avg_rain     | 4.711321428571425 | 4.6343473924412     

    As such, the range of non-outlier are:
    Metric       | Acceptable Values
    avg_icy_days | 2.50 - 77.78
    avg_snow     | 0 - 202.44    
    avg_rain     | 0 - 13.97
    '''
    modifier = 0

    min_icy_days = 2.5
    max_icy_days = 77.78

    max_snow = 202.44
    max_rain = 13.97

    if weather_dict['icy_days'] > max_icy_days:
        weather_dict['icy_days'] = max_icy_days

    if weather_dict['icy_days'] < min_icy_days:
        weather_dict['icy_days'] = min_icy_days

    if weather_dict['rain'] > max_rain:
        weather_dict['rain'] = max_rain

    if weather_dict['snow'] > max_snow:
        weather_dict['snow'] = max_snow

    # Icy days - note the adjustment for both ends of the range being valid outliers
    modifier += ((weather_dict['icy_days'] - min_icy_days) / (max_icy_days - min_icy_days)) * 2

    # Rain
    modifier += (weather_dict['rain'] / max_rain) * 2

    # Snow - note that since higher = better conditions, the percentage needs to be inverted
    modifier += (1 - (weather_dict['snow'] / max_snow)) * 2

    return modifier


def last_modified_date(path_to_file):
    stat = os.stat(path_to_file)
    epoch = stat.st_mtime
    return datetime.fromtimestamp(epoch).date()