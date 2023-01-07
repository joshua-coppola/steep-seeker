import matplotlib.pyplot as plt
import matplotlib as mpl
import sqlite3
import haversine as hs
from math import degrees, atan2
from os.path import exists
from os import makedirs
from rich.progress import track

import misc

mpl.use('svg')

def create_legend(x, y, direction, font_size, legend_offset):
    font_size = min(font_size, 8)
    # no legend on tiny maps
    if font_size <= 2.5:
        return

    # rotate points to look correct
    if 'n' in direction:
        x *= -1
        y *= -1
    if 'e' in direction:
        x *= -1
    if 'w' in direction:
        y *= -1
    if 's' in direction or 'n' in direction:
        temp = x
        x = y
        y = temp

    # plot hidden lines with labels for legend creation
    plt.plot(x, y, c='green', lw=0.001, label='Easy')
    plt.plot(x, y, c='royalblue', lw=0.001, label='Intermediate')
    plt.plot(x, y, c='black', lw=0.001, label='Advanced')
    plt.plot(x, y, c='red', lw=0.001, label='Expert')
    plt.plot(x, y, c='gold', lw=0.001, label='Extreme', )
    plt.plot(x, y, c='black', lw=0.001, linestyle='dotted', label='Gladed')

    # create the legend
    leg = plt.legend(fontsize=font_size, loc='lower center', bbox_to_anchor=(
        0.5, - legend_offset), frameon=False, ncol=3)

    fig = plt.gcf()
    # line width between .4 - 2
    line_width = max(min(fig.get_size_inches()[0] / 3, 2), .4)

    for row in leg.get_lines():
        row.set_linewidth(line_width)


def get_label_placement(x, y, length, name_length):
    if length == 0:
        print('Trail of 0 length found.')
        return (0, 0, 0)
    point_count = len(x)
    average_point_gap = length / point_count
    letter_size = 10 / average_point_gap
    label_length = average_point_gap * name_length * letter_size
    label_length_in_points = int(label_length / average_point_gap)

    # default answer is the middle of the trail
    point = int(point_count / 2)
    angle_list = []
    valid_list = []

    for i, _ in enumerate(x):
        valid = False
        if average_point_gap * i > label_length / 2.1:
            if average_point_gap * (point_count - i) > label_length / 2:
                valid = True
        if i == 0:
            ang = 0
        else:
            dx = x[i] - x[i-1]
            dy = y[i] - y[i-1]
            ang = degrees(atan2(dy, dx))
        angle_list.append(ang)
        valid_list.append(valid)

    best_answer = (1, 10000)
    for i, _ in enumerate(angle_list):
        if valid_list[i]:
            slice = angle_list[i - int(label_length_in_points / 2)
                                       : i + int(label_length_in_points / 2)]
            if len(slice) == 0:
                continue
            expected = sum(slice) / len(slice)
            error = sum([abs(i - expected) for i in slice])
            if error < best_answer[1]:
                best_answer = (i, error)
    if best_answer[1] != 0:
        point = best_answer[0]
    if point == 0:
        dx = dy = 0
    if point != 0:
        try:
            dx = x[point + int(label_length_in_points / 2)] - \
                x[point - int(label_length_in_points / 2)]
            dy = y[point + int(label_length_in_points / 2)] - \
                y[point - int(label_length_in_points / 2)]
        except:
            return(0, 0, 0)
    angle = degrees(atan2(dy, dx))
    if angle < -90:
        angle += 180
    if angle > 90:
        angle -= 180
    return(point, angle, label_length)


def populate_map(mountain_id, direction, with_labels=True, debug_mode=False):
    # configure correct item rotation & scaling
    lat_mirror = 1
    lon_mirror = -1
    flip_lat_lon = False
    if 'e' in direction:
        lat_mirror = -1
        lon_mirror = 1
    if 's' in direction:
        lon_mirror = 1
        flip_lat_lon = True
    if 'n' in direction:
        lat_mirror = -1
        flip_lat_lon = True
    if flip_lat_lon:
        temp = lat_mirror
        lat_mirror = lon_mirror
        lon_mirror = temp
        x_data = 'lon'
        y_data = 'lat'
    if not flip_lat_lon:
        x_data = 'lat'
        y_data = 'lon'

    fig = plt.gcf()
    # line width between .4 - 2
    line_width = max(min(fig.get_size_inches()[0] / 3, 2), .4)

    db = sqlite3.connect('data/db.db')
    cur = db.cursor()

    # lifts
    lift_list = cur.execute(
        'SELECT lift_id, name FROM Lifts WHERE mountain_id = ?', (mountain_id,)).fetchall()

    # convert results to dict
    desc = cur.description
    column_names = [col[0] for col in desc]
    lift_dict = [dict(zip(column_names, row)) for row in lift_list]

    # for each lift
    for lift in lift_dict:
        x = cur.execute(
            f"SELECT {x_data} FROM LiftPoints WHERE lift_id = {lift['lift_id']}").fetchall()
        y = cur.execute(
            f"SELECT {y_data} FROM LiftPoints WHERE lift_id = {lift['lift_id']}").fetchall()

        # remove the tuple of 1 item weirdness from the SQL query & reshape the data based on direction
        x = [i[0] * lat_mirror for i in x]
        y = [j[0] * lon_mirror for j in y]

        plt.plot(x, y, c='grey', lw=line_width)

        if with_labels:
            length = cur.execute(
                f"SELECT length FROM Lifts WHERE lift_id = {lift['lift_id']}").fetchall()[0][0]
            point, angle, label_length = get_label_placement(
                x, y, length, len(lift['name']))
            if point == 0 and angle == 0:
                continue
            # Check that label is shorter than trail
            label_text = lift['name']
            if label_text == '' and debug_mode:
                label_text = lift['lift_id']
            if label_length < length or debug_mode:
                plt.text(x[point], y[point], label_text, {'color': 'grey', 'size': 2, 'rotation': angle}, ha='center',
                         backgroundcolor='white', va='center', bbox=dict(boxstyle='square,pad=0.01', fc='white', ec='none'))

    # trails
    trail_list = cur.execute(
        'SELECT trail_id, name, area, gladed, steepest_30m FROM Trails WHERE mountain_id = ?', (mountain_id,)).fetchall()

    # convert results to dict
    desc = cur.description
    column_names = [col[0] for col in desc]
    trail_dict = [dict(zip(column_names, row)) for row in trail_list]

    # for each trail
    for trail in trail_dict:
        x = cur.execute(
            f"SELECT {x_data} FROM TrailPoints WHERE trail_id = {trail['trail_id']} AND for_display = 1").fetchall()
        y = cur.execute(
            f"SELECT {y_data} FROM TrailPoints WHERE trail_id = {trail['trail_id']} AND for_display = 1").fetchall()

        # remove the tuple of 1 item weirdness from the SQL query & reshape the data based on direction
        x = [i[0] * lat_mirror for i in x]
        y = [j[0] * lon_mirror for j in y]

        if debug_mode and trail['area']:
            debug_x = cur.execute(
                f"SELECT {x_data} FROM TrailPoints WHERE trail_id = {trail['trail_id']} AND for_display = 0").fetchall()
            debug_y = cur.execute(
                f"SELECT {y_data} FROM TrailPoints WHERE trail_id = {trail['trail_id']} AND for_display = 0").fetchall()

            # remove the tuple of 1 item weirdness from the SQL query & reshape the data based on direction
            debug_x = [i[0] * lat_mirror for i in debug_x]
            debug_y = [j[0] * lon_mirror for j in debug_y]

        color = misc.trail_color(trail['steepest_30m'], trail['gladed'])

        # place lines
        if trail['area'] == 'True':
            if trail['gladed'] == 'True':
                plt.fill(x, y, alpha=.1, fc=color)
                plt.fill(x, y, ec=color, fc='none',
                         linestyle='dashed', lw=line_width)
            if trail['gladed'] == 'False':
                plt.fill(x, y, alpha=.1, fc=color)
                plt.fill(x, y, ec=color, fc='none', lw=line_width)
            if debug_mode:
                if trail['gladed'] == 'True':
                    plt.plot(debug_x, debug_y, c=color, linestyle='dashed', lw=line_width)
                if trail['gladed'] == 'False':
                    plt.plot(debug_x, debug_y, c=color, lw=line_width)
        if trail['area'] == 'False':
            if trail['gladed'] == 'True':
                plt.plot(x, y, c=color, linestyle='dashed', lw=line_width)
            if trail['gladed'] == 'False':
                plt.plot(x, y, c=color, lw=line_width)

        # add label names
        if with_labels:
            length = cur.execute(
                f"SELECT length FROM Trails WHERE trail_id = {trail['trail_id']}").fetchall()[0][0]
            label_text = '{} {:.1f}{}'.format(
                trail['name'].strip(), trail['steepest_30m'], u'\N{DEGREE SIGN}')
            point, angle, label_length = get_label_placement(
                x, y, length, len(label_text))
            if point == 0 and angle == 0 and not debug_mode:
                continue
            # Check that label is shorter than trail
            if label_length < length or debug_mode:
                if trail['name'].strip() == '' and debug_mode:
                    label_text = trail['trail_id']
                # improves contrast
                if color == 'gold':
                    color = 'black'
                plt.text(x[point], y[point], label_text, {'color': color, 'size': 2, 'rotation': angle}, ha='center',
                         backgroundcolor='white', va='center', bbox=dict(boxstyle='square,pad=0.01', fc='white', ec='none'))


def find_map_size(mountain_id):
    db = sqlite3.connect('data/db.db')
    cur = db.cursor()

    trail_extremes = cur.execute(
        'SELECT MAX(lat), MIN(lat), MAX(lon), MIN(lon) FROM Mountains INNER JOIN Trails ON Mountains.mountain_id=Trails.mountain_id \
        INNER JOIN TrailPoints ON Trails.trail_id=TrailPoints.trail_id WHERE Trails.mountain_id = ?', (mountain_id,)).fetchall()[0]

    lift_extremes = cur.execute(
        'SELECT MAX(lat), MIN(lat), MAX(lon), MIN(lon) FROM Mountains INNER JOIN Lifts ON Mountains.mountain_id=Lifts.mountain_id \
        INNER JOIN LiftPoints ON Lifts.lift_id=LiftPoints.lift_id WHERE Lifts.mountain_id = ?', (mountain_id,)).fetchall()[0]

    # change in latitude (km)
    x_length = hs.haversine((max(trail_extremes[0], lift_extremes[0]), trail_extremes[2]), (min(
        trail_extremes[1], lift_extremes[1]), trail_extremes[2]), unit=hs.Unit.KILOMETERS)

    # change in longitude (km)
    y_length = hs.haversine((trail_extremes[0], max(trail_extremes[2], lift_extremes[2])), (
        trail_extremes[0], min(trail_extremes[3], lift_extremes[3])), unit=hs.Unit.KILOMETERS)

    direction = cur.execute(
        'SELECT direction FROM Mountains WHERE mountain_id = ?', (mountain_id,)).fetchall()[0][0]

    db.close()

    # rotate map to look correct
    if 's' in direction or 'n' in direction:
        temp = x_length
        x_length = y_length
        y_length = temp
    return(dict(x_length = x_length, y_length = y_length, x_point = trail_extremes[0], y_point = trail_extremes[2]))

def create_map(resort_name, state, with_labels=True, debug_mode=False):
    db = sqlite3.connect('data/db.db')
    cur = db.cursor()

    mountain_id = cur.execute(
        'SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?', (resort_name, state,),).fetchall()[0][0]

    direction = cur.execute(
        'SELECT direction FROM Mountains WHERE mountain_id = ?', (mountain_id,)).fetchall()[0][0]

    db.close()

    dimensions = find_map_size(mountain_id)
    x_length = dimensions['x_length']
    y_length = dimensions['y_length']
    # makes resort name between 5-25 font size depending on map size
    font_size = max(min(int(x_length*10), 25), 5)

    # create empty map
    plt.subplots(figsize=(x_length*2, ((y_length*2) + font_size * .04)))

    # configure empty map
    top_loc = (y_length*2) / ((y_length*2) + font_size * .02)
    bottom_loc = 1 - top_loc
    plt.title(resort_name, fontsize=font_size, y=1, pad=font_size * .5)

    plt.subplots_adjust(left=0, bottom=bottom_loc, right=1,
                        top=top_loc, wspace=0, hspace=0)
    plt.axis('off')
    plt.xticks([])
    plt.yticks([])

    if font_size > 16:
        font_size = 16
    if font_size == 5:
        plt.gcf().text(0.5, 0, 'Sources: USGS\nand OpenStreetMaps',
                       fontsize=font_size/2.3, ha='center', va='bottom')
    else:
        plt.gcf().text(0.5, 0, 'Sources: USGS and OpenStreetMaps',
                       fontsize=font_size/2.3, ha='center', va='bottom')

    # Compass Rose
    #rotate = 0
    # if direction == 's':
    #    rotate = 180
    # if direction == 'w':
    #    rotate = -90
    # if direction == 'e':
    #    rotate = 90
    # plt.gcf().text(.1, .1, '\u25b2\n\u25c1 N \u25b7\n\u25bd',
    #               ha='center', va='center', rotation=rotate, fontsize=font_size * .7)
    create_legend(dimensions['x_point'], dimensions['y_point'],
                  direction, font_size / 2, bottom_loc)

    populate_map(mountain_id, direction, with_labels, debug_mode)

    # save map
    if not exists(f'static/maps/{state}'):
        makedirs(f'static/maps/{state}')
    plt.savefig(f'static/maps/{state}/{resort_name}.svg', format='svg')
    plt.close()


def create_thumbnail(resort_name, state):
    db = sqlite3.connect('data/db.db')
    cur = db.cursor()

    mountain_id = cur.execute(
        'SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?', (resort_name, state,),).fetchall()[0][0]

    direction = cur.execute(
        'SELECT direction FROM Mountains WHERE mountain_id = ?', (mountain_id,)).fetchall()[0][0]

    db.close()

    dimensions = find_map_size(mountain_id)
    x_length = dimensions['x_length']
    y_length = dimensions['y_length']

    divisor = x_length * 2
    x_length = x_length / divisor
    y_length = y_length / divisor

    plt.subplots(figsize=(x_length*2, ((y_length*2))))

    plt.subplots_adjust(left=0, bottom=0, right=1,
                        top=1, wspace=0, hspace=0)
    plt.axis('off')
    plt.xticks([])
    plt.yticks([])

    populate_map(mountain_id, direction, False)

    # save map
    if not exists(f'static/thumbnails/{state}'):
        makedirs(f'static/thumbnails/{state}')
    plt.savefig(f'static/thumbnails/{state}/{resort_name}.svg', format='svg')
    plt.close()