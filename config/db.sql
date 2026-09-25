CREATE TABLE IF NOT EXISTS "Mountains"
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


CREATE TABLE IF NOT EXISTS "Trails"
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
    "multi_route" BOOLEAN NOT NULL,
    "ungroomed" BOOLEAN NOT NULL,
    "park" BOOLEAN NOT NULL,
    "hazardous" BOOLEAN NOT NULL,
    "length" REAL,
    "vertical" REAL,
    "difficulty" REAL,
    "max_slope" REAL,
    "average_slope" REAL,
    "steepest_100ft" REAL,
    "steepest_150ft" REAL,
    "steepest_300ft" REAL,
    "steepest_500ft" REAL,
    "steepest_1320ft" REAL,
    "steepest_2640ft" REAL,
    "steepest_5280ft" REAL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "ix_Trails_mountain_id" ON "Trails" ("mountain_id");
-- trail-rankings (the /trail-rankings nav link) scans every trail and
-- sorts by difficulty; this lets that page read straight down the index
CREATE INDEX IF NOT EXISTS "ix_Trails_difficulty" ON "Trails" ("difficulty");


CREATE TABLE IF NOT EXISTS "Lifts"
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

CREATE INDEX IF NOT EXISTS "ix_Lifts_mountain_id" ON "Lifts" ("mountain_id");


CREATE TABLE IF NOT EXISTS "Blacklist"
(
    "item_id" TEXT PRIMARY KEY NOT NULL,
    "mountain_id" TEXT NOT NULL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "ix_Blacklist_mountain_id" ON "Blacklist" ("mountain_id");


CREATE TABLE IF NOT EXISTS "WeatherCalibration"
(
    "id" INTEGER PRIMARY KEY CHECK ("id" = 1),
    "created" TIMESTAMP NOT NULL,
    "n_resorts" INTEGER NOT NULL,
    "icy_days" TEXT NOT NULL,
    "rain" TEXT NOT NULL,
    "snow" TEXT NOT NULL
);
