import sqlite3
from math import sqrt
import matplotlib.pyplot as plt

import db as database
import _misc

cur, db = database.db_connect()

def print_dict(dic: dict(), title: str) -> None:
    max_len_col_1 = len(title[0])
    for key, value in dic.items():
        if len(key) > max_len_col_1:
            max_len_col_1 = len(key)
    print(f"\n{title[0]}{' ' * (max_len_col_1 - len(title[0]))} | {title[1]}")
    for key, value in dic.items():
        print(f"{key}{' ' * (max_len_col_1 - len(key))} | {value}")

print('Weather: 6pts')
print('Gladed: 5.5pts')
print('Ungroomed: 2.5pts')

def trail_rating(pitch: float, gladed: str, ungroomed: str, weather_modifier: float) -> 'str':
    pitch += (weather_modifier / 6) * 6.5
    if gladed == True:
        pitch += 5.5
    if ungroomed == True:
        pitch += 2.5
    # 0-16 degrees: green
    if pitch < 18:
        return 'easy'
    # 16-23 degrees: blue
    if pitch < 27:
        return 'intermediate'
    # 23-32 degrees: black
    if pitch < 36:
        return 'advanced'
    # 32-45 degrees: red
    elif pitch < 47:
        return 'expert'
    # >45 degrees: yellow
    else:
        return 'extreme'

def convert_to_numeric(rating: str) -> int:
    if rating == 'novice' or rating == 'easy':
        return 1
    if rating == 'intermediate':
        return 2
    if rating == 'advanced':
        return 3
    if rating == 'expert':
        return 4
    if rating == 'extreme':
        return 5
    return 0

def compute_accuracy(all_trails: list(tuple())) -> None:

    trail_accuracy = []
    for trail in all_trails:
        weather_modifier = get_weather_data(trail[4])
        rating = trail_rating(trail[0], trail[1], trail[2], weather_modifier)
        trail_accuracy.append((trail[3], rating))

    count_correct = 0
    count_within_1 = 0
    count_within_2 = 0
    count_invalid = 0
    miss_dict = {}
    for row in trail_accuracy:
        numeric_official = convert_to_numeric(row[0])
        numeric_computed = convert_to_numeric(row[1])
        if numeric_official == 0 or numeric_computed == 0:
            count_invalid += 1
            continue
        if abs(numeric_official - numeric_computed) <= 1:
            count_within_1 += 1
        if abs(numeric_official - numeric_computed) <= 2:
            count_within_2 += 1
        if numeric_computed == numeric_official:
            count_correct += 1
            continue
        try:
            miss_dict[f'{numeric_official}->{numeric_computed}'] += 1
        except:
            miss_dict[f'{numeric_official}->{numeric_computed}'] = 1

    print(f'\n{round((count_correct/ (len(trail_accuracy) - count_invalid))*100, 3)}% Correct')
    print(f'{round((count_within_1/ (len(trail_accuracy) - count_invalid))*100, 3)}% Within 1 rating')
    print(f'{round((count_within_2/ (len(trail_accuracy) - count_invalid))*100, 3)}% Within 2 ratings')
    print_dict(miss_dict, ['Official->Calc', 'Count'])

def get_weather_data(mountain_id):
    conn = database.dict_cursor()
    query = 'SELECT avg_icy_days, avg_snow, avg_rain FROM Mountains WHERE mountain_id = ?'

    weather_dict = conn.execute(query, (mountain_id,)).fetchone()
    formatted_dict = {}
    formatted_dict['icy_days'] = weather_dict['avg_icy_days']
    formatted_dict['rain'] = weather_dict['avg_rain']
    formatted_dict['snow'] = weather_dict['avg_snow']

    return _misc.get_weather_modifier(formatted_dict)

steepest_pitch = 'steepest_30m'
#print(steepest_pitch)

query = f'SELECT {steepest_pitch}, gladed, ungroomed FROM Trails'

all_trails = cur.execute(query).fetchall()
x = [x[0] for x in all_trails]

plt.hist(x)
plt.title('All Trails')
#plt.show()

gladed_pitch = {}
for gladed in [True, False]:
    query = f'SELECT AVG({steepest_pitch}) FROM Trails WHERE gladed= ?'
    params = (gladed,)

    gladed_pitch[gladed] = cur.execute(query, params).fetchall()[0][0]

gladed_pitch['Difference'] = gladed_pitch['True'] - gladed_pitch['False']
print_dict(gladed_pitch, ['Gladed', 'Average Pitch'])

gladed_sd = {}
for gladed in [True, False]:
    query = f'SELECT AVG({steepest_pitch} * {steepest_pitch}) - (AVG({steepest_pitch}) * AVG({steepest_pitch})) FROM Trails WHERE gladed = ?'
    params = (gladed,)

    gladed_sd[gladed] = sqrt(cur.execute(query, params).fetchall()[0][0])

print_dict(gladed_sd, ['Gladed', 'Standard Deviation'])

query = f'SELECT {steepest_pitch}, gladed, ungroomed FROM Trails WHERE gladed = "True"'

all_gladed_trails = cur.execute(query).fetchall()
x = [x[0] for x in all_gladed_trails]

plt.hist(x)
plt.title('Gladed Trails')
#plt.show()

for official_rating in ['novice', 'easy', 'intermediate', 'advanced', 'expert', 'extreme', 'freeride']:
    print(official_rating)
    ungroomed_pitch = {}
    for ungroomed in [True, False]:
        query = f'SELECT AVG({steepest_pitch}) FROM Trails WHERE ungroomed= ? AND official_rating = ?'
        params = (ungroomed, official_rating)

        ungroomed_pitch[ungroomed] = cur.execute(query, params).fetchall()[0][0]

    try:
        ungroomed_pitch['Difference'] = ungroomed_pitch['True'] - ungroomed_pitch['False']
        print_dict(ungroomed_pitch, ['Ungroomed', 'Average Pitch'])
    except:
        continue
    

official_rating_pitch = {}
for value in ['novice', 'easy', 'intermediate', 'advanced', 'expert', 'extreme', 'freeride']:
    query = f'SELECT AVG({steepest_pitch}) FROM Trails WHERE official_rating = ?'
    params = (value,)

    official_rating_pitch[value] = cur.execute(query, params).fetchall()[0][0]

print_dict(official_rating_pitch, ['Official Rating', 'Average Pitch'])

official_rating_sd = {}
for value in ['novice', 'easy', 'intermediate', 'advanced', 'expert', 'extreme', 'freeride']:
    query = f'SELECT AVG({steepest_pitch} * {steepest_pitch}) - (AVG({steepest_pitch}) * AVG({steepest_pitch})) FROM Trails WHERE official_rating = ?'
    params = (value,)

    official_rating_sd[value] = sqrt(cur.execute(query, params).fetchall()[0][0])

print_dict(official_rating_sd, ['Official Rating', 'Standard Deviation'])

for value in ['novice', 'easy', 'intermediate', 'advanced', 'expert', 'extreme', 'freeride']:
    query = f'SELECT {steepest_pitch} FROM Trails WHERE official_rating = ?'
    params = (value,)

    trails_by_rating = cur.execute(query, params).fetchall()
    x = [x[0] for x in trails_by_rating]

    plt.hist(x)
    plt.title(f'{value} Trails')
    #plt.show()

query = f'SELECT {steepest_pitch}, gladed, ungroomed, official_rating, mountain_id FROM Trails WHERE {steepest_pitch} > 0'
all_trails = cur.execute(query).fetchall()

compute_accuracy(all_trails)

for region in ['northeast', 'southeast', 'midwest', 'west']:
    print(f'\n{region}\n')
    query = f'SELECT {steepest_pitch}, gladed, ungroomed, official_rating, Trails.mountain_id FROM Mountains INNER JOIN Trails ON Mountains.mountain_id=Trails.mountain_id WHERE Mountains.region = ?'
    trails = cur.execute(query, (region,)).fetchall()

    compute_accuracy(trails)

weather_mean = {}
for column in ['avg_icy_days', 'avg_snow', 'avg_rain']:
    query = f'SELECT AVG({column}) FROM Mountains WHERE {column} > 0'

    weather_mean[column] = cur.execute(query).fetchall()[0][0]

print_dict(weather_mean, ['Metric', 'Mean'])    

weather_sd = {}
for column in ['avg_icy_days', 'avg_snow', 'avg_rain']:
    query = f'SELECT AVG({column} * {column}) - (AVG({column}) * AVG({column})) FROM Mountains'

    weather_sd[column] = sqrt(cur.execute(query).fetchall()[0][0])

print_dict(weather_sd, ['Metric', 'Standard Deviation'])
