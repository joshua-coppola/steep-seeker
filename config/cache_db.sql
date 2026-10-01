CREATE TABLE IF NOT EXISTS "CachedPoints"
(
    "point" TEXT PRIMARY KEY NOT NULL,
    "elevation" REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS "CachedWeather"
(
    "point" TEXT NOT NULL,
    "season" INTEGER NOT NULL,  -- calendar year the winter starts (November)
    "month" INTEGER NOT NULL,   -- calendar month: 11, 12, 1, 2, 3, 4
    "icy_days" INTEGER NOT NULL,
    "rain" REAL NOT NULL,
    "snow" REAL NOT NULL,
    PRIMARY KEY ("point", "season", "month")
);
