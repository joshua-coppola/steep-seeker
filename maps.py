import matplotlib.pyplot as plt
import matplotlib as mpl
import haversine as hs
from math import degrees, atan2
from os.path import exists
from os import makedirs

import _misc
import db
from mountain import Mountain, Trail, Lift

mpl.use("svg")


def create_legend(
    x: float, y: float, direction: str, font_size: float, legend_offset: float
) -> None:
    font_size = min(font_size, 8)
    # no legend on tiny maps
    if font_size <= 2.5:
        return

    # rotate points to look correct
    if "n" in direction:
        x *= -1
        y *= -1
    if "e" in direction:
        x *= -1
    if "w" in direction:
        y *= -1
    if "s" in direction or "n" in direction:
        temp = x
        x = y
        y = temp

    # plot hidden lines with labels for legend creation
    plt.plot(x, y, c="green", lw=0.001, label="Easy")
    plt.plot(x, y, c="royalblue", lw=0.001, label="Intermediate")
    plt.plot(x, y, c="black", lw=0.001, label="Advanced")
    plt.plot(x, y, c="red", lw=0.001, label="Expert")
    plt.plot(
        x,
        y,
        c="gold",
        lw=0.001,
        label="Extreme",
    )
    plt.plot(x, y, c="black", lw=0.001, linestyle="dotted", label="Gladed")

    # create the legend
    leg = plt.legend(
        fontsize=font_size,
        loc="lower center",
        bbox_to_anchor=(0.5, -legend_offset),
        frameon=False,
        ncol=3,
    )

    fig = plt.gcf()
    # line width between .4 - 2
    line_width = max(min(fig.get_size_inches()[0] / 3, 2), 0.4)

    for row in leg.get_lines():
        row.set_linewidth(line_width)


def get_label_placement(
    x: list(), y: list(), length: float, name_length: int
) -> tuple():
    if length == 0:
        print("Trail of 0 length found.")
        return (0, 0, 0)
    point_count = len(x)
    average_point_gap = length / point_count
    letter_size = 22 / average_point_gap
    label_length = average_point_gap * name_length * letter_size
    label_length_in_points = int(label_length / average_point_gap)

    # default answer is the middle of the trail
    point = int(point_count / 2)
    angle_list = []
    valid_list = []

    for i, _ in enumerate(x):
        valid = False
        if average_point_gap * i > label_length / 2:
            if average_point_gap * (point_count - i) > label_length / 2:
                valid = True
        if i == 0:
            ang = 0
        else:
            dx = x[i] - x[i - 1]
            dy = y[i] - y[i - 1]
            ang = degrees(atan2(dy, dx))
        angle_list.append(ang)
        valid_list.append(valid)

    best_answer = (1, 10000)
    for i, _ in enumerate(angle_list):
        if valid_list[i]:
            slice = angle_list[
                i - int(label_length_in_points / 2) : i
                + int(label_length_in_points / 2)
            ]
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
        half = int(label_length_in_points / 2)
        low = point - half
        high = point + half

        # Check that indices are within bounds
        if low < 0 or high >= len(x) or high >= len(y):
            return (0, 0, 0)

        dx = x[high] - x[low]
        dy = y[high] - y[low]

    angle = degrees(atan2(dy, dx))
    if angle < -90:
        angle += 180
    if angle > 90:
        angle -= 180
    return (point, angle, label_length)


def populate_map(
    mountain_info, with_labels: bool = True, debug_mode: bool = False
) -> None:
    # configure correct item rotation & scaling
    lat_mirror = 1
    lon_mirror = -1
    flip_lat_lon = False
    if "e" in mountain_info.direction:
        lat_mirror = -1
        lon_mirror = 1
    if "s" in mountain_info.direction:
        lon_mirror = 1
        flip_lat_lon = True
    if "n" in mountain_info.direction:
        lat_mirror = -1
        flip_lat_lon = True
    if flip_lat_lon:
        temp = lat_mirror
        lat_mirror = lon_mirror
        lon_mirror = temp
        x_data = "lon"
    if not flip_lat_lon:
        x_data = "lat"

    fig = plt.gcf()
    # line width between .4 - 2
    line_width = max(min(fig.get_size_inches()[0] / 3, 2), 0.4)

    # lifts
    for lift_obj in mountain_info.lifts():
        lift = Lift(lift_obj["lift_id"])
        if x_data == "lat":
            x = lift.lat()
            y = lift.lon()

        if x_data == "lon":
            x = lift.lon()
            y = lift.lat()

        x = [j * lat_mirror for j in x]
        y = [k * lon_mirror for k in y]

        plt.plot(x, y, c="grey", lw=line_width)

        if with_labels:
            point, angle, label_length = get_label_placement(
                x, y, lift.length, len(lift.name)
            )
            if point == 0 and angle == 0:
                continue
            # Check that label is shorter than trail
            label_text = lift.name
            if label_text == "" and debug_mode:
                label_text = lift.lift_id
            if label_length < lift.length or debug_mode:
                plt.text(
                    x[point],
                    y[point],
                    label_text,
                    {"color": "grey", "size": 2, "rotation": angle},
                    ha="center",
                    backgroundcolor="white",
                    va="center",
                    bbox=dict(boxstyle="square,pad=0.01", fc="white", ec="none"),
                )

    # trails
    for trail_obj in mountain_info.trails():
        trail = Trail(trail_obj["trail_id"])
        if x_data == "lat":
            x = trail.lat()
            y = trail.lon()

        if x_data == "lon":
            x = trail.lon()
            y = trail.lat()

        x = [j * lat_mirror for j in x]
        y = [k * lon_mirror for k in y]

        if debug_mode and trail.area:
            if x_data == "lat":
                debug_x = trail.lat(visible=False)
                debug_y = trail.lon(visible=False)

            if x_data == "lon":
                debug_x = trail.lon(visible=False)
                debug_y = trail.lat(visible=False)

            debug_x = [j * lat_mirror for j in debug_x]
            debug_y = [k * lon_mirror for k in debug_y]

        color = _misc.trail_color(trail.difficulty)

        # place lines
        if trail.area:
            if trail.gladed:
                plt.fill(x, y, alpha=0.1, fc=color)
                plt.fill(x, y, ec=color, fc="none", linestyle="dashed", lw=line_width)
            if not trail.gladed:
                plt.fill(x, y, alpha=0.1, fc=color)
                plt.fill(x, y, ec=color, fc="none", lw=line_width)
            if debug_mode:
                if trail.gladed:
                    plt.plot(
                        debug_x, debug_y, c=color, linestyle="dashed", lw=line_width
                    )
                if not trail.gladed:
                    plt.plot(debug_x, debug_y, c=color, lw=line_width)
        if not trail.area:
            if trail.gladed:
                plt.plot(x, y, c=color, linestyle="dashed", lw=line_width)
            if not trail.gladed:
                plt.plot(x, y, c=color, lw=line_width)

        # add label names
        if with_labels:
            label_text = "{} {:.1f}{}".format(
                trail.name.strip(), trail.steepest_30m, "\N{DEGREE SIGN}"
            )
            point, angle, label_length = get_label_placement(
                x, y, trail.length, len(label_text)
            )
            if point == 0 and angle == 0 and not debug_mode:
                continue
            # Check that label is shorter than trail
            if label_length < trail.length or debug_mode:
                if trail.name.strip() == "" and debug_mode:
                    label_text = trail.trail_id
                # improves contrast
                if color == "gold":
                    color = "black"
                plt.text(
                    x[point],
                    y[point],
                    label_text,
                    {"color": color, "size": 2, "rotation": angle},
                    ha="center",
                    backgroundcolor="white",
                    va="center",
                    bbox=dict(boxstyle="square,pad=0.01", fc="white", ec="none"),
                )


def find_map_size(mountain_info) -> dict():
    conn = db.tuple_cursor()

    query_trails = """
        SELECT MAX(TrailPoints.lat), MIN(TrailPoints.lat),
            MAX(TrailPoints.lon), MIN(TrailPoints.lon)
        FROM Mountains
        INNER JOIN Trails ON Mountains.mountain_id = Trails.mountain_id
        INNER JOIN TrailPoints ON Trails.trail_id = TrailPoints.trail_id
        WHERE Trails.mountain_id = ?
    """
    trail_extremes = conn.execute(query_trails, (mountain_info.mountain_id,)).fetchone()

    query_lifts = """
        SELECT MAX(LiftPoints.lat), MIN(LiftPoints.lat),
            MAX(LiftPoints.lon), MIN(LiftPoints.lon)
        FROM Mountains
        INNER JOIN Lifts ON Mountains.mountain_id = Lifts.mountain_id
        INNER JOIN LiftPoints ON Lifts.lift_id = LiftPoints.lift_id
        WHERE Lifts.mountain_id = ?
    """
    lift_extremes = conn.execute(query_lifts, (mountain_info.mountain_id,)).fetchone()

    conn.close()

    # Unpack or default to trail_extremes values
    try:
        max_lat = max(filter(None, [trail_extremes[0], lift_extremes[0]]))
        min_lat = min(filter(None, [trail_extremes[1], lift_extremes[1]]))
        max_lon = max(filter(None, [trail_extremes[2], lift_extremes[2]]))
        min_lon = min(filter(None, [trail_extremes[3], lift_extremes[3]]))
    except (TypeError, ValueError):
        # fallback to trail_extremes only
        max_lat, min_lat = trail_extremes[0], trail_extremes[1]
        max_lon, min_lon = trail_extremes[2], trail_extremes[3]

    # Compute distances
    x_length = hs.haversine(
        (max_lat, max_lon), (min_lat, max_lon), unit=hs.Unit.KILOMETERS
    )
    y_length = hs.haversine(
        (max_lat, max_lon), (max_lat, min_lon), unit=hs.Unit.KILOMETERS
    )

    # rotate map to look correct
    if "s" in mountain_info.direction or "n" in mountain_info.direction:
        temp = x_length
        x_length = y_length
        y_length = temp
    return dict(
        x_length=x_length,
        y_length=y_length,
        x_point=trail_extremes[0],
        y_point=trail_extremes[2],
    )


def create_map(
    resort_name: str, state: str, with_labels: bool = True, debug_mode: bool = False
) -> None:
    mountain_info = Mountain(resort_name, state)

    dimensions = find_map_size(mountain_info)
    x_length = dimensions["x_length"]
    y_length = dimensions["y_length"]
    # makes resort name between 5-25 font size depending on map size
    font_size = max(min(int(x_length * 10), 25), 5)

    # create empty map
    plt.subplots(figsize=(x_length * 2, ((y_length * 2) + font_size * 0.04)))

    # configure empty map
    top_loc = (y_length * 2) / ((y_length * 2) + font_size * 0.02)
    bottom_loc = 1 - top_loc
    plt.title(resort_name, fontsize=font_size, y=1, pad=font_size * 0.5)

    plt.subplots_adjust(
        left=0, bottom=bottom_loc, right=1, top=top_loc, wspace=0, hspace=0
    )
    plt.axis("off")
    plt.xticks([])
    plt.yticks([])

    if font_size > 16:
        font_size = 16
    if font_size == 5:
        plt.gcf().text(
            0.5,
            0,
            "Sources: USGS\nand OpenStreetMaps",
            fontsize=font_size / 2.3,
            ha="center",
            va="bottom",
        )
    else:
        plt.gcf().text(
            0.5,
            0,
            "Sources: USGS and OpenStreetMaps",
            fontsize=font_size / 2.3,
            ha="center",
            va="bottom",
        )

    create_legend(
        dimensions["x_point"],
        dimensions["y_point"],
        mountain_info.direction,
        font_size / 2,
        bottom_loc,
    )

    populate_map(mountain_info, with_labels, debug_mode)

    # save map
    if not exists(f"static/maps/{state}"):
        makedirs(f"static/maps/{state}")
    plt.savefig(f"static/maps/{state}/{resort_name}.svg", format="svg")
    plt.close()


def create_thumbnail(resort_name: str, state: str) -> None:
    mountain_info = Mountain(resort_name, state)

    dimensions = find_map_size(mountain_info)
    x_length = dimensions["x_length"]
    y_length = dimensions["y_length"]

    divisor = x_length * 2
    x_length = x_length / divisor
    y_length = y_length / divisor

    plt.subplots(figsize=(x_length * 2, (y_length * 2)))

    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    plt.axis("off")
    plt.xticks([])
    plt.yticks([])

    populate_map(mountain_info, False)

    # save map
    if not exists(f"static/thumbnails/{state}"):
        makedirs(f"static/thumbnails/{state}")
    plt.savefig(f"static/thumbnails/{state}/{resort_name}.svg", format="svg")
    plt.close()
