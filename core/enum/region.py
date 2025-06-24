from enum import Enum
from typing import Self

from core.enum.state import State


class Region(Enum):
    NORTHEAST = [
        State.MAINE,
        State.NEW_HAMPSHIRE,
        State.VERMONT,
        State.NEW_YORK,
        State.MASSACHUSETTS,
        State.RHODE_ISLAND,
        State.CONNECTICUT,
        State.PENNSYLVANIA,
        State.NEW_JERSEY,
    ]
    SOUTHEAST = [
        State.MARYLAND,
        State.DELAWARE,
        State.VIRGINIA,
        State.WEST_VIRGINIA,
        State.KENTUCKY,
        State.TENNESSEE,
        State.NORTH_CAROLINA,
        State.SOUTH_CAROLINA,
        State.GEORGIA,
        State.FLORIDA,
        State.ALABAMA,
        State.MISSISSIPPI,
        State.LOUISIANA,
        State.ARKANSAS,
    ]
    MIDWEST = [
        State.NORTH_DAKOTA,
        State.SOUTH_DAKOTA,
        State.MINNESOTA,
        State.WISCONSIN,
        State.MICHIGAN,
        State.OHIO,
        State.INDIANA,
        State.ILLINOIS,
        State.IOWA,
        State.NEBRASKA,
        State.KANSAS,
        State.MISSOURI,
        State.OKLAHOMA,
        State.TEXAS,
    ]
    WEST = [
        State.NEW_MEXICO,
        State.ARIZONA,
        State.CALIFORNIA,
        State.NEVADA,
        State.UTAH,
        State.COLORADO,
        State.WYOMING,
        State.IDAHO,
        State.OREGON,
        State.WASHINGTON,
        State.MONTANA,
        State.ALASKA,
        State.HAWAII,
    ]

    def get_region(state: State) -> Self:
        if state in Region.NORTHEAST.value:
            return Region.NORTHEAST
        if state in Region.SOUTHEAST.value:
            return Region.SOUTHEAST
        if state in Region.MIDWEST.value:
            return Region.MIDWEST
        if state in Region.WEST.value:
            return Region.WEST
        raise ValueError(f"Invalid State Object: {state}")
