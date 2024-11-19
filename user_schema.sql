DROP TABLE IF EXISTS Log;

CREATE TABLE "Log"
(
    "timestamp" TIMESTAMP NOT NULL,
    "ip" TEXT NOT NULL,
    "page_category" TEXT NOT NULL,
    "page_visited" TEXT NOT NULL,
    "parameters" TEXT,
    PRIMARY KEY ("timestamp", "ip")
)
