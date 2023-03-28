# steep-seeker

Steep Seeker is a website that presents a standardized rating system to allow skiers to compare trails or resorts. Ever wonder how your local resort's definition of a black diamond stacks up to others? The goal of this rating system is to provide hard truths to questions like these. Resorts rate their trails relative only to the other trails at the resort, and as such there is tremendous variance between mountains, and especially between regions.

Steep Seeker is an evolution of [https://github.com/joshua-coppola/Ski-Trail-Ratings] and can be seen as a V2.

The project can be viewed live at [https://steepseeker.com].

## Installation

Start by cloning this repo into the desired location. The program works on both Windows and Linux, but this section assumes a linux system will be used.

Next, install pip if you do not already have it. This can be done with:

```bash
sudo apt install python3-pip
```

Once pip is installed, the next step is the project's dependencies, which can be install with:

```bash
pip install rich flask flask_wtf flask-sitemapper matplotlib haversine requests
```

Mark `startup.sh` as executable with `chmod +x`. Run `startup.sh` in order to add necessary directories and your secret file.

If you are exporting data from a previous install, it can be found in the `data` directory and the `static/maps` and `static/thumbnails` directories.

To run the website on localhost, execute the file called `app.py` with `python3 app.py`. If the port specified in the `app.py` file is less than 5000, sudo is required.

## Status

### Overall

- [x] Add mobile support
- [ ] Add footer
- [ ] Improve comments on code

### Python

- [x] Add mountain, trail, and lift classes
- [x] Add weather data to difficulty ratings
- [x] Add type hinting to functions

### Landing Page

- [ ] Make layout less plain

### Search

- Reasonably complete

### Mountain Rankings

- [ ] Add better filters
- [ ] Improve appearance

### Trail Rankings

- [x] Add ability to sort by each pitch length
- [x] Improve appearance

### Maps

- [ ] 3d maps
- [ ] Leaflet / interactive maps

### Management

- [ ] Create management page
- [ ] Add logins

### Maps to fix

- Echo Mountain - Title & sources cut off
- Kendall Mountain - Title cut off
- Telluride - normal trails marked as areas
- Appalachian Ski Mountain - title cut off

### Mountains with no trails/lifts (not a complete list)

- Barker Mountain
- China Peak
- Coppervale
- Hidden Valley, OH
- Paoli Peaks
  