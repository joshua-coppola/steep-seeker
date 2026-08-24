"""
Renders a mountain's trails and lifts to an SVG map (create_map) and a
label-free SVG thumbnail (create_thumbnail), colored by trail difficulty.
Operates entirely on an already-loaded core.support.mountain.Mountain --
no DB access happens in this module.
"""

from math import atan2, degrees
from os import makedirs
from os.path import exists

import haversine as hs
import matplotlib as mpl
import matplotlib.pyplot as plt

from core.support.mountain import Mountain

mpl.use("svg")

METERS_TO_FEET = 3.28084


def _trail_color(difficulty: float) -> str:
    # 0-18 degrees: green
    if difficulty < 18:
        return "green"
    # 18-27 degrees: blue
    if difficulty < 27:
        return "royalblue"
    # 27-36 degrees: black
    if difficulty < 36:
        return "black"
    # 36-47 degrees: red
    if difficulty < 47:
        return "red"
    # >47 degrees: yellow
    return "gold"


def _xy_from_coords(coords) -> tuple[list[float], list[float]]:
    lons = []
    lats = []
    for point in coords:
        lons.append(point[0])
        lats.append(point[1])
    return lons, lats


def _create_legend(
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
        x, y = y, x

    # plot hidden lines with labels for legend creation
    plt.plot(x, y, c="green", lw=0.001, label="Easy")
    plt.plot(x, y, c="royalblue", lw=0.001, label="Intermediate")
    plt.plot(x, y, c="black", lw=0.001, label="Advanced")
    plt.plot(x, y, c="red", lw=0.001, label="Expert")
    plt.plot(x, y, c="gold", lw=0.001, label="Extreme")
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


def _get_label_placement(
    x: list[float], y: list[float], length: float, name_length: int
) -> tuple[int, float, float]:
    if length == 0:
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
        valid = (
            average_point_gap * i > label_length / 2
            and average_point_gap * (point_count - i) > label_length / 2
        )
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
            angle_slice = angle_list[
                i - int(label_length_in_points / 2) : i
                + int(label_length_in_points / 2)
            ]
            if len(angle_slice) == 0:
                continue
            expected = sum(angle_slice) / len(angle_slice)
            error = sum([abs(i - expected) for i in angle_slice])
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


def _find_map_size(mountain: Mountain) -> dict:
    trail_lons: list[float] = []
    trail_lats: list[float] = []
    for trail in mountain.trails.values():
        coords = trail.geometry.exterior.coords if trail.area else trail.geometry.coords
        lons, lats = _xy_from_coords(coords)
        trail_lons.extend(lons)
        trail_lats.extend(lats)

    lift_lons: list[float] = []
    lift_lats: list[float] = []
    for lift in mountain.lifts.values():
        lons, lats = _xy_from_coords(lift.geometry.coords)
        lift_lons.extend(lons)
        lift_lats.extend(lats)

    trail_max_lat = max(trail_lats)
    trail_max_lon = max(trail_lons)

    all_lats = trail_lats + lift_lats
    all_lons = trail_lons + lift_lons
    max_lat, min_lat = max(all_lats), min(all_lats)
    max_lon, min_lon = max(all_lons), min(all_lons)

    # Compute distances
    x_length = hs.haversine(
        (max_lat, max_lon), (min_lat, max_lon), unit=hs.Unit.KILOMETERS
    )
    y_length = hs.haversine(
        (max_lat, max_lon), (max_lat, min_lon), unit=hs.Unit.KILOMETERS
    )

    # rotate map to look correct
    if "s" in mountain.direction or "n" in mountain.direction:
        x_length, y_length = y_length, x_length

    return {
        "x_length": x_length,
        "y_length": y_length,
        "x_point": trail_max_lat,
        "y_point": trail_max_lon,
    }


def _populate_map(
    mountain: Mountain, with_labels: bool = True, debug_mode: bool = False
) -> None:
    # configure correct item rotation & scaling
    lat_mirror = 1
    lon_mirror = -1
    flip_lat_lon = False
    direction = mountain.direction
    if "e" in direction:
        lat_mirror = -1
        lon_mirror = 1
    if "s" in direction:
        lon_mirror = 1
        flip_lat_lon = True
    if "n" in direction:
        lat_mirror = -1
        flip_lat_lon = True
    if flip_lat_lon:
        lat_mirror, lon_mirror = lon_mirror, lat_mirror
        x_data = "lon"
    else:
        x_data = "lat"

    fig = plt.gcf()
    # line width between .4 - 2
    line_width = max(min(fig.get_size_inches()[0] / 3, 2), 0.4)

    # lifts
    for lift in mountain.lifts.values():
        lons, lats = _xy_from_coords(lift.geometry.coords)
        if x_data == "lat":
            x, y = lats, lons
        else:
            x, y = lons, lats

        x = [j * lat_mirror for j in x]
        y = [k * lon_mirror for k in y]

        plt.plot(x, y, c="grey", lw=line_width)

        if with_labels:
            length_feet = (lift.length or 0) * METERS_TO_FEET
            point, angle, label_length = _get_label_placement(
                x, y, length_feet, len(lift.name)
            )
            if point == 0 and angle == 0:
                continue
            # Check that label is shorter than trail
            label_text = lift.name
            if label_text == "" and debug_mode:
                label_text = lift.lift_id
            if label_length < length_feet or debug_mode:
                plt.text(
                    x[point],
                    y[point],
                    label_text,
                    {"color": "grey", "size": 2, "rotation": angle},
                    ha="center",
                    backgroundcolor="white",
                    va="center",
                    bbox={"boxstyle": "square,pad=0.01", "fc": "white", "ec": "none"},
                )

    # trails
    for trail in mountain.trails.values():
        coords = trail.geometry.exterior.coords if trail.area else trail.geometry.coords
        lons, lats = _xy_from_coords(coords)
        if x_data == "lat":
            x, y = lats, lons
        else:
            x, y = lons, lats

        x = [j * lat_mirror for j in x]
        y = [k * lon_mirror for k in y]

        if debug_mode and trail.area and trail.route is not None:
            debug_lons, debug_lats = _xy_from_coords(trail.route.coords)
            if x_data == "lat":
                debug_x, debug_y = debug_lats, debug_lons
            else:
                debug_x, debug_y = debug_lons, debug_lats

            debug_x = [j * lat_mirror for j in debug_x]
            debug_y = [k * lon_mirror for k in debug_y]

        color = _trail_color(trail.difficulty)

        # place lines
        if trail.area:
            if trail.gladed:
                plt.fill(x, y, alpha=0.1, fc=color)
                plt.fill(x, y, ec=color, fc="none", linestyle="dashed", lw=line_width)
            else:
                plt.fill(x, y, alpha=0.1, fc=color)
                plt.fill(x, y, ec=color, fc="none", lw=line_width)
            if debug_mode and trail.route is not None:
                if trail.gladed:
                    plt.plot(
                        debug_x, debug_y, c=color, linestyle="dashed", lw=line_width
                    )
                else:
                    plt.plot(debug_x, debug_y, c=color, lw=line_width)
        else:
            if trail.gladed:
                plt.plot(x, y, c=color, linestyle="dashed", lw=line_width)
            else:
                plt.plot(x, y, c=color, lw=line_width)

        # add label names
        if with_labels:
            label_text = "{} {:.1f}{}".format(
                trail.name.strip(), trail.steepest_30m, "\N{DEGREE SIGN}"
            )
            length_feet = (trail.length or 0) * METERS_TO_FEET
            point, angle, label_length = _get_label_placement(
                x, y, length_feet, len(label_text)
            )
            if point == 0 and angle == 0 and not debug_mode:
                continue
            # Check that label is shorter than trail
            if label_length < length_feet or debug_mode:
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
                    bbox={"boxstyle": "square,pad=0.01", "fc": "white", "ec": "none"},
                )


def create_map(
    mountain: Mountain,
    output_dir: str = "static/maps",
    with_labels: bool = True,
    debug_mode: bool = False,
) -> None:
    dimensions = _find_map_size(mountain)
    x_length = dimensions["x_length"]
    y_length = dimensions["y_length"]
    # makes resort name between 5-25 font size depending on map size
    font_size = max(min(int(x_length * 10), 25), 5)

    # create empty map
    plt.subplots(figsize=(x_length * 2, ((y_length * 2) + font_size * 0.04)))

    # configure empty map
    top_loc = (y_length * 2) / ((y_length * 2) + font_size * 0.02)
    bottom_loc = 1 - top_loc
    plt.title(mountain.name, fontsize=font_size, y=1, pad=font_size * 0.5)

    plt.subplots_adjust(
        left=0, bottom=bottom_loc, right=1, top=top_loc, wspace=0, hspace=0
    )
    plt.axis("off")
    plt.xticks([])
    plt.yticks([])

    font_size = min(font_size, 16)
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

    _create_legend(
        dimensions["x_point"],
        dimensions["y_point"],
        mountain.direction,
        font_size / 2,
        bottom_loc,
    )

    _populate_map(mountain, with_labels, debug_mode)

    # save map
    state_dir = f"{output_dir}/{mountain.state.value}"
    if not exists(state_dir):
        makedirs(state_dir)
    plt.savefig(f"{state_dir}/{mountain.name}.svg", format="svg")
    plt.close()


def create_thumbnail(mountain: Mountain, output_dir: str = "static/thumbnails") -> None:
    dimensions = _find_map_size(mountain)
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

    _populate_map(mountain, False)

    # save map
    state_dir = f"{output_dir}/{mountain.state.value}"
    if not exists(state_dir):
        makedirs(state_dir)
    plt.savefig(f"{state_dir}/{mountain.name}.svg", format="svg")
    plt.close()
