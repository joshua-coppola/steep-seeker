from dataclasses import dataclass


@dataclass
class LiftIcon:
    """
    One of icons_src/'s lift badges: its file in static/icons/ (minus .svg),
    its alt/title text, and its kind, which base.css sizes it by. Rendered
    by templates/lift_icons.jinja.
    """

    file: str
    label: str
    kind: str


# chair seats -> (icon file, label)
CHAIR_ICONS = {
    1: ("single_chair", "Single chair"),
    2: ("double_chair", "Double chair"),
    3: ("triple_chair", "Triple chair"),
    4: ("quad_chair", "Quad chair"),
    6: ("six_pack_chair", "Six-pack chair"),
    8: ("eight_pack_chair", "Eight-pack chair"),
}
# the chair sizes there's a bubble icon for (no doubles/triples have one)
BUBBLE_CHAIR_SIZES = {4, 6, 8}
# enclosed-cabin lift types, which share the gondola icon -> label
CABIN_LIFT_LABELS = {"gondola": "Gondola", "cable_car": "Tram"}
# lift types that pull or carry riders along the snow
SURFACE_LIFT_TYPES = {
    "t-bar",
    "j-bar",
    "platter",
    "drag_lift",
    "rope_tow",
    "magic_carpet",
}


def lift_icons(
    lift_type: str | None,
    occupancy: int | None,
    bubble: bool | None,
    detachable: bool | None,
    heating: bool | None,
) -> list[LiftIcon]:
    """
    The badges shown beside a lift's name (the lift rankings page, the map
    pages' sidebar and popups): its chair size (with a bubble, for the sizes
    drawn with one), a gondola/tram, or a surface lift, then express
    (detachable) and heated. Lifts no icon fits, like chairs of unknown size,
    get just the express/heated ones.
    """
    icons = []
    if lift_type == "chair_lift" and occupancy in CHAIR_ICONS:
        file, label = CHAIR_ICONS[occupancy]
        if bubble and occupancy in BUBBLE_CHAIR_SIZES:
            icons.append(
                LiftIcon(
                    f"{file.removesuffix('_chair')}_bubble_chair",
                    f"Bubble {label.lower()}",
                    "chair",
                )
            )
        else:
            icons.append(LiftIcon(file, label, "chair"))
    elif lift_type in CABIN_LIFT_LABELS:
        icons.append(LiftIcon("gondola", CABIN_LIFT_LABELS[lift_type], "gondola"))
    elif lift_type in SURFACE_LIFT_TYPES:
        icons.append(LiftIcon("surface_lift", "Surface lift", "surface"))
    if detachable:
        icons.append(LiftIcon("express", "Express (detachable)", "express"))
    if heating:
        icons.append(LiftIcon("heated", "Heated", "heated"))
    return icons
