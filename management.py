import sys
import sqlite3
from flask import Flask, render_template, json, redirect, url_for, request, flash, session, request
from flask_wtf import FlaskForm
import os
from math import sqrt, degrees, atan2

import _flask_api as api
import db as database
import _misc
from mountain import Mountain, Trail, Lift
import main

api.nav_links.append(api.navigationLink('Management', 'management', '/management'))

class managementButton:
    def __init__(self, title, to):
        self.title = title
        self.to = to

options = []
options.append(managementButton('Add Resort', '/management-add-resort'))
options.append(managementButton('Edit Resort', '/management-edit-resort'))
options.append(managementButton('Delete Resort', '/management-delete-resort'))

@api.app.route('/management')
def management():
    return render_template('management.jinja', nav_links=api.nav_links, management_links=options, active_page='management')

@api.app.route('/management-add-resort')
def management_add_resort():
    available_resorts = []
    for item in os.listdir('data/osm'):
        if item.endswith('.osm'):
            available_resorts.append(item.split('.')[0])
    return render_template('management-add-resort.jinja', nav_links=api.nav_links, management_links=options, active_page='Add Resort', resorts=available_resorts)

@api.app.route('/management-edit-resort')
def management_edit_resort():
    def get_label_orientation(lon_points, lat_points):
        midpoint = int(len(lon_points) / 2)
        dx = lon_points[max(midpoint - 5, 0)] - lon_points[min(midpoint + 5, (midpoint * 2) - 1)]
        dy = lat_points[max(midpoint - 5, 0)] - lat_points[min(midpoint + 5, (midpoint * 2) - 1)]
        ang = degrees(atan2(dy, dx))
        orientation = 0
        if abs(ang) < 90 and not trail.area and mountain.direction == 's':
            orientation = 180
        if abs(ang) > 90 and not trail.area and mountain.direction == 'n':
            orientation = 180
        if ang > 0 and not trail.area and mountain.direction == 'w':
            orientation = 180
        if ang < 0 and not trail.area and mountain.direction == 'e':
            orientation = 180

        return orientation

    geojson = {'type':'FeatureCollection', 'features':[]}
    
    q = request.args.get('q')
    if q:
        rename = request.args.get('rename')
        full_refresh = request.args.get('full_refresh')
        stats_refresh = request.args.get('map_refresh')
        map_refresh = request.args.get('map_refresh')
        ignore_areas = request.args.get('ignore_areas')
        size_increase = request.args.get('size_increase')

        if size_increase:
            size_increase = float(size_increase)

        if not ignore_areas:
            ignore_areas = False

        name, state = q.split(', ')

        if full_refresh:
            print(type(size_increase))
            print(size_increase)
            main.refresh_resort_from_osm(name, state, size_increase)
        else:
            if stats_refresh:
                main.refresh_resort(name, state, ignore_areas)
            if map_refresh:
                main.maps.create_map(name, state)
                main.maps.create_thumbnail(name, state)
        
        
        mountain = Mountain(name, state)

        if rename:
            main.rename_resort(name, state, rename)

            mountain = Mountain(rename, state)

        trails = [Trail(trail['trail_id']) for trail in mountain.trails()]
    
        lifts = [Lift(lift['lift_id']) for lift in mountain.lifts()]

        for trail in trails:
            geom_type = 'LineString'
            if trail.area:
                geom_type = 'Polygon'
            feature = {'type':'Feature',
                    'properties':{},
                    'geometry':{'type': geom_type,
                                'coordinates':[]}}
            coords = list(zip(trail.lon(), trail.lat()))
            coords = [list(element) for element in coords]
            if trail.area:
                coords.append(coords[0])
                coords = [coords]
            feature['geometry']['coordinates'] = coords
            popup_content = f'<h3>{trail.name}</h3><p>Rating: {trail.difficulty}<span class="icon difficulty-{_misc.trail_color(trail.difficulty)}"></span></p>'
            popup_content += f'<p>Length: {trail.length} ft</p><p>Vertical Drop: {trail.vertical} ft</p>'
            if trail.steepest_30m:
                popup_content += f'<p>30m Pitch: {trail.steepest_30m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_30m)}"></span>'
            if trail.steepest_50m:
                popup_content += f'<p>50m Pitch: {trail.steepest_50m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_50m)}"></span>'
            if trail.steepest_100m:
                popup_content += f'<p>100m Pitch: {trail.steepest_100m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_100m)}"></span>'
            if trail.steepest_200m:
                popup_content += f'<p>200m Pitch: {trail.steepest_200m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_200m)}"></span>'
            if trail.steepest_500m:
                popup_content += f'<p>500m Pitch: {trail.steepest_500m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_500m)}"></span>'
            if trail.steepest_1000m:
                popup_content += f'<p>1000m Pitch: {trail.steepest_1000m}' + u'\N{DEGREE SIGN}' + f'<span class="icon difficulty-{_misc.trail_color(trail.steepest_1000m)}"></span>'
            popup_content += f'<p>Trail ID: {trail.trail_id}</p>'
        
            feature['properties']['popupContent'] = popup_content
            feature['properties']['label'] = f'{trail.name}'
            
            lon_points = trail.lon()
            lat_points = trail.lat()

            orientation = get_label_orientation(lon_points, lat_points)
            
            feature['properties']['orientation'] = orientation
            feature['properties']['color'] = _misc.trail_color(trail.difficulty)
            feature['properties']['gladed'] = str(trail.gladed)

            geojson['features'].append(feature)

        for lift in lifts:
            feature = {'type':'Feature',
                    'properties':{},
                    'geometry':{'type': 'LineString',
                                'coordinates':[]}}
            coords = list(zip(lift.lon(), lift.lat()))
            coords = [list(element) for element in coords]
            feature['geometry']['coordinates'] = coords
            popup_content = f'<h3>{lift.name}</h3><p>Length: {lift.length} ft</p>'
            popup_content += f'<p>Lift ID: {lift.lift_id}</p>'
            feature['properties']['popupContent'] = popup_content
            feature['properties']['label'] = f'{lift.name}'
            
            lon_points = lift.lon()
            lat_points = lift.lat()

            orientation = get_label_orientation(lon_points, lat_points)
            feature['properties']['orientation'] = orientation
            feature['properties']['color'] = 'grey'

            geojson['features'].append(feature)
    if not q:
        mountain = Mountain(None, None)
        mountain.name = ''

    mountains = database.get_mountains()
    mountains_output = sorted([f'{name}, {state}' for name, state in mountains])

    return render_template('management-edit-resort.jinja', nav_links=api.nav_links, management_links=options, active_page='Edit Resort', resorts=mountains_output, mountain=mountain, geojson=geojson)

api.app.run(host='0.0.0.0', port=5000, debug=False)