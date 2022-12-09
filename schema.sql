
DROP TABLE IF EXISTS Mountains;

CREATE TABLE "Mountains"
(
    "mountain_id" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT NOT NULL,
    "state" TEXT NOT NULL,
    "region" TEXT NOT NULL,
    "direction" TEXT,
    "trail_count" INTEGER NOT NULL,
    "lift_count" INTEGER NOT NULL,
    "vertical" INTEGER,
    "difficulty" REAL,
    "beginner_friendliness" REAL
);


DROP TABLE IF EXISTS Trails;

CREATE TABLE "Trails"
(
    "trail_id" INTEGER PRIMARY KEY NOT NULL,
    "mountain_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "area" BOOLEAN NOT NULL,
    "gladed" BOOLEAN NOT NULL,
    "official_rating" REAL,
    "steepest_30m" REAL,
    "steepest_50m" REAL,
    "steepest_100m" REAL,
    "steepest_200m" REAL,
    "steepest_500m" REAL,
    "steepest_1000m" REAL,
    "vertical_drop" REAL,
    "length" REAL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);


DROP TABLE IF EXISTS Lifts;

CREATE TABLE "Lifts"
(
    "lift_id" INTEGER PRIMARY KEY NOT NULL,
    "mountain_id" INTEGER NOT NULL,
    "name" TEXT NOT NULL,
    "length" REAL,
    FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);


DROP TABLE IF EXISTS TrailPoints;

CREATE TABLE "TrailPoints"
(
    "ind" INTEGER NOT NULL,
    "trail_id" INTEGER NOT NULL,
    "for_display" INTEGER NOT NULL,
    "lat" DECIMAL(9,6) NOT NULL,
    "lon" DECIMAL(9,6) NOT NULL,
    "elevation" REAL,
    "slope" REAL,
    PRIMARY KEY("ind","trail_id", "for_display"),
    FOREIGN KEY("trail_id") REFERENCES "Trails"("trail_id") ON DELETE CASCADE
);

CREATE INDEX "TrailCoordinates"
ON "TrailPoints"("lat", "lon")

CREATE INDEX "TrailId"
ON "TrailPoints"("trail_id")


DROP TABLE IF EXISTS LiftPoints;

CREATE TABLE "LiftPoints"
(
    "ind" INTEGER NOT NULL,
    "lift_id" INTEGER NOT NULL,
    "lat" DECIMAL(9,6) NOT NULL,
    "lon" DECIMAL(9,6) NOT NULL,
    "elevation" REAL,
    PRIMARY KEY("ind","lift_id"),
    FOREIGN KEY("lift_id") REFERENCES "Lifts"("lift_id") ON DELETE CASCADE
);

CREATE INDEX "LiftCoordinates"
ON "LiftPoints"("lat", "lon")

CREATE INDEX "LiftId"
ON "LiftPoints"("lift_id")

DROP TABLE IF EXISTS CachedPoints;

CREATE TABLE "CachedPoints"
(
    "lat" DECIMAL(9,6) NOT NULL,
    "lon" DECIMAL(9,6) NOT NULL,
    "elevation" REAL,
    PRIMARY KEY("lat", "lon")
);
