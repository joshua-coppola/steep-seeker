from dataclasses import dataclass

from flask import Blueprint, render_template

web = Blueprint("web", __name__)


@dataclass
class NavigationLink:
    title: str
    page: str
    to: str


nav_links = [
    NavigationLink("About", "about", "/about"),
    NavigationLink("Search", "search", "/search"),
    NavigationLink("Explore Map", "explore_map", "/explore-map"),
    NavigationLink(
        "Mountain Rankings",
        "rankings",
        "/rankings?sort=difficulty&order=desc&region=usa",
    ),
    NavigationLink("Trail Rankings", "trail_rankings", "/trail-rankings?region=usa"),
    NavigationLink("Lift Rankings", "lift_rankings", "/lift-rankings?region=usa"),
    NavigationLink("Random Mountain", "random_map", "/random-mountain"),
]


@web.route("/")
def index():
    return render_template("index.jinja", nav_links=nav_links, active_page="index")


@web.route("/about")
def about():
    return render_template("about.jinja", nav_links=nav_links, active_page="about")
