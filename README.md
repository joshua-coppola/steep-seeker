# steep-seeker

Steep Seeker is a website that presents a standardized rating system to allow skiers to compare trails or resorts. Ever wonder how your local resort's definition of a black diamond stacks up to others? The goal of this rating system is to provide hard truths to questions like these. Resorts rate their trails relative only to the other trails at the resort, and as such there is tremendous variance between mountains, and especially between regions.

Steep Seeker is an evolution of [https://github.com/joshua-coppola/Ski-Trail-Ratings] and can be seen as a V2.

## Installation

Start by cloning this repo into the desired location. The program works on both Windows and Linux, but this section assumes a linux system will be used.

Next, install pip if you do not already have it. This can be done with:

```bash
sudo apt install python3-pip
```

Once pip is installed, the next step is the project's dependencies, which can be install with:

```bash
pip install rich flask flask_wtf matplotlib haversine requests
```

Mark `startup.sh` as executable with `chmod +x`. Run `startup.sh` in order to add necessary directories and your secret file.

If you are exporting data from a previous install, it can be found in the `data` directory and the `static/maps` and `static/thumbnails` directories.

To run the website on localhost, execute the file called `app.py` with `python3 app.py`. If the port specified in the `app.py` file is less than 5000, sudo is required.

## Upcoming

### Known Bugs

- [x] Legends do not scale correctly on smaller maps anymore
- [x] Compass rose placement can be iffy on some mountains
- [x] Area trail names do not display
- [x] Lifts do not have elevation
- [x] Cache struggles with floating point errors, leads to about 90% success rate
- [x] Cache fetch is slow, 30s for 3000 points
- [x] Program hangs between processing trails and lifts
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
- Pico - Outlaw piste type, many trails named the same
- Smuggler's Notch - 22 unnamed trails
- Stowe - 7 unnamed trails & many with same name, grab new OSM file
- Heavenly - 24 unnamed trails
- Mammoth - 35 unnamed trails
- Palisades Tahoe - 182 unnamed trails
- Echo Mountain - Title & sources cut off
- Kendall Mountain - Title cut off
- Sunlight - no trail names
- Telluride - normal trails marked as areas
- Nashoba Valley - All trails are areas
- Catamount - almost no trail names
- Eaton - no names at all
- Appalachian Ski Mountain - title cut off

### Mountains with no trails/lifts (not a complete list)

- Barker Mountain
- China Peak
- Coppervale
  