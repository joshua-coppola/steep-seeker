
DROP TABLE IF EXISTS Mountains;

CREATE TABLE "Mountains"
(
  "mountain_id" INTEGER PRIMARY KEY NOT NULL,
  "osm_file_name" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "state" TEXT NOT NULL,
  "region" TEXT NOT NULL,
  "direction" TEXT NOT NULL,
  "trail_count" INTEGER NOT NULL,
  "lift_count" INTEGER NOT NULL,
  "vertical" INTEGER NOT NULL,
  "difficulty" REAL NOT NULL,
  "beginner_friendliness" REAL NOT NULL
);


DROP TABLE IF EXISTS Trails;

CREATE TABLE "Trails"
(
  "trail_id" INTEGER PRIMARY KEY NOT NULL,
  "mountain_id" INTEGER NOT NULL,
  "name" TEXT NOT NULL,
  "is_area" INTEGER NOT NULL,
  "difficulty" REAL NOT NULL,
  "difficulty_modifier" REAL NOT NULL,
  "steepest_pitch" REAL NOT NULL,
  "vertical_drop" REAL NOT NULL,
  "length" REAL NOT NULL,
  FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);


DROP TABLE IF EXISTS Lifts;

CREATE TABLE "Lifts"
(
  "lift_id" INTEGER PRIMARY KEY NOT NULL,
  "mountain_id" INTEGER NOT NULL,
  "name" TEXT NOT NULL,
  FOREIGN KEY("mountain_id") REFERENCES "Mountains"("mountain_id") ON DELETE CASCADE
);


DROP TABLE IF EXISTS TrailPoints;

CREATE TABLE "TrailPoints"
(
  "ind" INTEGER NOT NULL,
  "trail_id" INTEGER NOT NULL,
  "for_display" INTEGER NOT NULL,
  "latitude" REAL NOT NULL,
  "longitude" REAL NOT NULL,
  "elevation" REAL NOT NULL,
  "slope" REAL NOT NULL,
  PRIMARY KEY("ind","trail_id", "for_display"),
  FOREIGN KEY("trail_id") REFERENCES "Trails"("trail_id") ON DELETE CASCADE
);


DROP TABLE IF EXISTS LiftPoints;

CREATE TABLE "LiftPoints"
(
  "ind" INTEGER NOT NULL,
  "lift_id" INTEGER NOT NULL,
  "latitude" REAL NOT NULL,
  "longitude" REAL NOT NULL,
  "elevation" REAL NOT NULL,
  PRIMARY KEY("ind","lift_id"),
  FOREIGN KEY("lift_id") REFERENCES "Lifts"("lift_id") ON DELETE CASCADE
);
