import osmium
from decimal import Decimal


class OSMHandler(osmium.SimpleHandler):
    """
    Reads in an OSM file, and returns a Handler
    object with a nodes, ways, and relations
    dict as objects

    Example usage:

    osm_handler = OSMHandler()
    osm_handler.apply_file("data/osm/VT/Okemo.osm")
    nodes = osm_handler.nodes
    """

    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.nodes = {}
        self.ways = {}
        self.relations = {}

    def node(self, n):
        self.nodes[n.id] = {
            "lat": round(Decimal(n.lat), 6),
            "lon": round(Decimal(n.lon), 6),
        }

    def way(self, w):
        nodes = [node.ref for node in w.nodes]
        tags = {tag.k: tag.v for tag in w.tags}
        self.ways[f"w{w.id}"] = {"nodes": nodes, "tags": tags}

    def relation(self, r):
        members = [f"w{member.ref}" for member in r.members]
        tags = {tag.k: tag.v for tag in r.tags}
        self.relations[f"r{r.id}"] = {"members": members, "tags": tags}
