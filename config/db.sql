
DROP TABLE IF EXISTS Mountains;

CREATE TABLE "Mountains"
(
    "mountain_id" TEXT PRIMARY KEY NOT NULL,
    "name" TEXT NOT NULL,
    "state" TEXT NOT NULL,
    "direction" TEXT NOT NULL,
    "coordinates" TEXT,
    "season_passes" TEXT,
    "vertical" INTEGER,
    "difficulty" REAL,
    "beginner_friendliness" REAL,
    "average_icy_days" REAL,
    "average_snow" REAL,
    "average_rain" REAL,
    "last_updated" TIMESTAMP,
    "url" TEXT
);


DROP TABLE IF EXISTS Trails;

CREATE TABLE "Trails"
(
    "trail_id" TEXT PRIMARY KEY NOT NULL,
    "mountain_id" TEXT NOT NULL,
    "geometry" TEXT NOT NULL,
    "interior_geometry" TEXT,
    "route" TEXT,
    "name" TEXT NOT NULL,
    "official_rating" TEXT,
    "gladed" BOOLEAN NOT NULL,
    "area" BOOLEAN NOT NULL,
    "ungroomed" BOOLEAN NOT NULL,
    "park" BOOLEAN NOT NULL,
    "length" REAL,
    "vertical" REAL,
    "difficulty" REAL,
    "max_slope" REAL,
    "average_slope" REAL,
    "steepest_30m" REAL,
    "steepest_50m" REAL,
    "steepest_100m" REAL,
    "steepest_200m" REAL,
    "steepest_500m" REAL,
    "steepest_1000m" REAL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);

CREATE INDEX "ix_Trails_mountain_id" ON "Trails" ("mountain_id");
-- trail-rankings (the /trail-rankings nav link) scans every trail and
-- sorts by difficulty; this lets that page read straight down the index
CREATE INDEX "ix_Trails_difficulty" ON "Trails" ("difficulty");


DROP TABLE IF EXISTS Lifts;

CREATE TABLE "Lifts"
(
    "lift_id" TEXT PRIMARY KEY NOT NULL,
    "mountain_id" TEXT NOT NULL,
    "geometry" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "lift_type" TEXT NOT NULL,
    "occupancy" INTEGER,
    "capacity" INTEGER,
    "detachable" BOOLEAN,
    "bubble" BOOLEAN,
    "heating" BOOLEAN,
    "length" REAL,
    "vertical" REAL,
    "average_slope" REAL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);

CREATE INDEX "ix_Lifts_mountain_id" ON "Lifts" ("mountain_id");


DROP TABLE IF EXISTS Blacklist;

CREATE TABLE "Blacklist"
(
    "item_id" TEXT PRIMARY KEY NOT NULL,
    "mountain_id" TEXT NOT NULL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);

CREATE INDEX "ix_Blacklist_mountain_id" ON "Blacklist" ("mountain_id");
