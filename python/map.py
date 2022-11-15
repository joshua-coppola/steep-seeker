import matplotlib.pyplot as plt
import sqlite3
import haversine as hs


def create_legend(x, y, direction, font_size, legend_offset):
    font_size = min(font_size, 8)

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


def create_map(resort_name, state):
    db = sqlite3.connect('data/db.db')
    cur = db.cursor()

    mountain_id = cur.execute(
        'SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?', (resort_name, state,),).fetchall()[0]

    trail_extremes = cur.execute(
        'SELECT MAX(lat), MIN(lat), MAX(lon), MIN(lon) FROM Mountains INNER JOIN Trails ON Mountains.mountain_id=Trails.mountain_id \
        INNER JOIN TrailPoints ON Trails.trail_id=TrailPoints.trail_id WHERE Trails.mountain_id = ?', (mountain_id)).fetchall()[0]

    lift_extremes = cur.execute(
        'SELECT MAX(lat), MIN(lat), MAX(lon), MIN(lon) FROM Mountains INNER JOIN Lifts ON Mountains.mountain_id=Lifts.mountain_id \
        INNER JOIN LiftPoints ON Lifts.lift_id=LiftPoints.lift_id WHERE Lifts.mountain_id = ?', (mountain_id)).fetchall()[0]

    # change in latitude (km)
    x_length = hs.haversine((max(trail_extremes[0], lift_extremes[0]), trail_extremes[2]), (max(
        trail_extremes[1], lift_extremes[1]), trail_extremes[2]), unit=hs.Unit.KILOMETERS)

    # change in longitude (km)
    y_length = hs.haversine((trail_extremes[0], max(trail_extremes[2], lift_extremes[2])), (
        trail_extremes[0], max(trail_extremes[3], lift_extremes[3])), unit=hs.Unit.KILOMETERS)

    direction = cur.execute(
        'SELECT direction FROM Mountains WHERE mountain_id = ?', (mountain_id)).fetchall()[0][0]

    # rotate map to look correct
    if 's' in direction or 'n' in direction:
        temp = x_length
        x_length = y_length
        y_length = temp

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
    plt.gcf().text(0.5, 0, 'Sources: USGS and OpenStreetMaps',
                   fontsize=font_size/2.3, ha='center', va='bottom')

    # Compass Rose
    rotate = 0
    if direction == 's':
        rotate = 180
    if direction == 'w':
        rotate = -90
    if direction == 'e':
        rotate = 90
    plt.gcf().text(.1, .1, '\u25b2\n\u25c1 N \u25b7\n\u25bd',
                   ha='center', va='center', rotation=rotate, fontsize=font_size * .7)
    create_legend(trail_extremes[0], trail_extremes[2],
                  direction, font_size, bottom_loc)

    plt.show()


create_map('Okemo', 'VT')
