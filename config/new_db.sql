
DROP TABLE IF EXISTS Mountains;

CREATE TABLE "Mountains"
(
    "mountain_id" INTEGER PRIMARY KEY NOT NULL,
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
    "mountain_id" INTEGER NOT NULL,
    "geometry" TEXT NOT NULL,
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
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);


DROP TABLE IF EXISTS Lifts;

CREATE TABLE "Lifts"
(
    "lift_id" INTEGER PRIMARY KEY NOT NULL,
    "mountain_id" INTEGER NOT NULL,
    "geometry" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "lift_type" TEXT NOT NULL,
    "occupancy" INTEGER NOT NULL,
    "capacity" INTEGER NOT NULL,
    "detachable" BOOLEAN NOT NULL,
    "bubble" BOOLEAN NOT NULL,
    "heated" BOOLEAN NOT NULL,
    "length" REAL,
    "vertical" REAL,
    "average_slope" REAL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);
