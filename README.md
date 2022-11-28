# steep-seeker

Steep Seeker is a website that presents a standardized rating system to allow skiers to compare trails or resorts. Ever wonder how your local resort's definition of a black diamond stacks up to others? The goal of this rating system is to provide hard truths to questions like these. Resorts rate their trails relative only to the other trails at the resort, and as such there is tremendous variance between mountains, and especially between regions.

Steep Seeker is an evolution of [https://github.com/joshua-coppola/Ski-Trail-Ratings] and can be seen as a V2.

## Upcoming

### Known Bugs

- [x] Legends do not scale correctly on smaller maps anymore
- [ ] Compass rose placement can be iffy on some mountains
- [x] Area trail names do not display
- [x] Lifts do not have elevation
- [ ] Cache struggles with floating point errors, leads to about 90% success rate
- [x] Legends display on tiny maps, leading to them being cutoff

### Features

- [x] Auto detect mountain direction
- [x] Loading Indicators
- [ ] Use API to fetch OSM files for new resorts
- [ ] Integrate with website
- [ ] Management interface to fix maps from
- [x] Use cached elevations

### Maps to fix

- Burke - rotate?
- Killington - 10 unnamed trails, many duplicates
- Mad River Glen - 13  unnamed trails, many duplicates
- Magic - 16 unnamed trails, many duplicates
- Mount Snow - 5 unnamed trails, 1 piste type, jagged trails
- Pico - Outlaw piste type, many trails named the same, 'A slope' is rated -14 degrees
- Smuggler's Notch - 22 unnamed trails
- Stowe - 7 unnamed trails & many with same name, grab new OSM file
- Sugarbush - 9 unnamed trails
