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

@api.app.route('/management')
def management():
    return render_template(
        'management.jinja',
        nav_links=api.nav_links,
        management_links=options,
        active_page='management'
    )

@api.app.route('/management-add-resort', methods=['GET', 'POST'])
def management_add_resort():
    available_resorts = []
    for item in os.listdir('data/osm'):
        if item.endswith('.osm'):
            available_resorts.append(item.split('.')[0])
    
    if request.method == 'POST':
        # Check if user selected from dropdown
        q = request.form.get('q')
        
        # Check if user uploaded a file
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '' and file.filename.endswith('.osm'):
                # Save the uploaded file
                filename = file.filename
                filepath = os.path.join('data/osm', filename)
                file.save(filepath)
                
                # Use the uploaded file name (without .osm extension)
                q = filename.rsplit('.', 1)[0]
        
        # Process the resort (either from dropdown or uploaded file)
        if q and q != 'none':
            name, state = main.add_resort(q)
            query_param = f"{name}, {state}"
            return redirect(url_for('management_edit_resort', q=query_param))
    
    return render_template(
        'management-add-resort.jinja',
        nav_links=api.nav_links,
        management_links=options,
        active_page='Add Resort',
        resorts=available_resorts
    )

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
        name, state = q.split(', ')

    delete_resort = request.args.get('delete_resort')
    rename = request.args.get('rename')

    if delete_resort == 'DELETE': 
        main.delete_resort(name, state)
        q = None

    if q:
        full_refresh = request.args.get('full_refresh')
        stats_refresh = request.args.get('stats_refresh')
        map_refresh = request.args.get('map_refresh')
        ignore_areas = request.args.get('ignore_areas')
        size_increase = request.args.get('size_increase')
        rotate = request.args.get('rotate')
        delete = request.args.get('delete')
        blacklist = request.args.get('blacklist')
        trail_id = request.args.get('trail_id')
        url = request.args.get('url')
        update_passes = request.args.get('update_passes')

        if update_passes:
            pass_list = []
            epic = request.args.get('epic')
            if epic:
                pass_list.append('Epic')
            ikon = request.args.get('ikon')
            if ikon:
                pass_list.append('Ikon')
            mountain_collective = request.args.get('mountain_collective')
            if mountain_collective:
                pass_list.append('Mountain Collective')
            indy = request.args.get('indy')
            if indy:
                pass_list.append('Indy')
            cooper = request.args.get('cooper')
            if cooper:
                pass_list.append('Cooper')
            powder_alliance = request.args.get('powder_alliance')
            if powder_alliance:
                pass_list.append('Powder Alliance')
            freedom_pass = request.args.get('freedom')
            if freedom_pass:
                pass_list.append('Freedom')
            powder_pass = request.args.get('power')
            if powder_pass:
                pass_list.append('Power')

            if len(pass_list) > 0:
                database._set_mountain_season_passes(name, state, ','.join(pass_list))
            else:
                database._set_mountain_season_passes(name, state, None)


        if size_increase:
            size_increase = float(size_increase)

        if not ignore_areas:
            ignore_areas = False

        if full_refresh:
            main.refresh_resort_from_osm(name, state, size_increase)
        else:
            if stats_refresh:
                main.refresh_resort(name, state, ignore_areas)
            if map_refresh:
                main.maps.create_map(name, state)
                main.maps.create_thumbnail(name, state)

        if rotate:
            main.rotate_map_clockwise(name, state)

        if trail_id:
            gladed = request.args.get('gladed')
            ungroomed = request.args.get('ungroomed')
            area = request.args.get('area')

            if not gladed:
                gladed = False
            if not ungroomed:
                ungroomed = False
            if not area:
                area = False

            database.change_trail_stats(name, state, trail_id, gladed, ungroomed, area)


        if delete:
            main.delete_item(name, state, delete, blacklist)


        if url:
            database._set_url(name, state, url)
        
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
            trail_points = list(zip(trail.lat(), trail.lon(), trail.elevation()))
            trail_points = _misc.get_slope(trail_points)
            coords = [[element[1], element[0], int(float(element[2]) * 100 / (2.54 * 12)), element[3]] for element in trail_points]

            if trail.area:
                coords.append(coords[0])
                coords = [coords]
            feature['geometry']['coordinates'] = coords
            if trail.gladed:
                gladed = '<i class="icon gladed"></i>'
            else:
                gladed = ''
            if trail.ungroomed:
                ungroomed = '<span>&nbsp;&nbsp;</span><i class="icon ungroomed"></i>'
            else:
                ungroomed = ''
            popup_content = f'<h3>{trail.name}{gladed}{ungroomed}</h3>'
            popup_content += f'<p>OSM ID: {trail.trail_id}</p>'
            popup_content += f'<p>Rating: {trail.difficulty}<span class="icon difficulty-{_misc.trail_color(trail.difficulty)}"></span></p>'
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
            
            popup_content += '<form id="update_tags" class="search-form">'
            popup_content += f'<input type="hidden" name="q" id="q" value="{name}, {state}">'
            popup_content += f'<input type="hidden" name="trail_id" id="trail_id" value="{trail.trail_id}">'
            if trail.gladed:
                checked = 'checked'
            else:
                checked = ''
            popup_content += f'<input type="checkbox" id="gladed" name="gladed" value=True {checked}>'
            popup_content += '<label for="gladed">Gladed</label>'
            if trail.ungroomed:
                checked = 'checked'
            else:
                checked = ''
            popup_content += f'<input type="checkbox" id="ungroomed" name="ungroomed" value=True {checked}>'
            popup_content += '<label for="ungroomed">Ungroomed</label>'
            if trail.area:
                checked = 'checked'
            else:
                checked = ''
            popup_content += f'<input type="checkbox" id="area" name="area" value=True {checked}>'
            popup_content += '<label for="area">Area</label><br>'
            popup_content += '<input class="button-cta" id="update_tags_submit" type="submit" value="Update" /></form>'

            popup_content += '<form id="delete" class="search-form">'
            popup_content += f'<input type="hidden" name="q" id="q" value="{name}, {state}">'
            popup_content += f'<input type="hidden" name="delete" id="delete_item" value="{trail.trail_id}">'
            popup_content += '<input type="checkbox" id="blacklist" name="blacklist" value=True>'
            popup_content += '<label for="blacklist">Blacklist</label><br>'
            popup_content += '<input class="button-cta" id="delete_submit" type="submit" value="Delete" /></form>'
        
            feature['properties']['popupContent'] = popup_content
            feature['properties']['label'] = f'{trail.name}'
            
            lon_points = trail.lon()
            lat_points = trail.lat()

            orientation = get_label_orientation(lon_points, lat_points)
            
            feature['properties']['orientation'] = orientation
            feature['properties']['color'] = _misc.trail_color(trail.difficulty)
            feature['properties']['gladed'] = str(trail.gladed)
            feature['properties']['difficulty_modifier'] = trail.difficulty - trail.steepest_30m

            geojson['features'].append(feature)

        if len(trails) > 0:
            whole_resort_modifier = trails[0].difficulty - trails[0].steepest_30m - (trails[0].gladed * 5.5) - (trails[0].ungroomed * 2.5)
        else:
            whole_resort_modifier = 0

        for lift in lifts:
            feature = {'type':'Feature',
                    'properties':{},
                    'geometry':{'type': 'LineString',
                                'coordinates':[]}}
            lift_points = list(zip(lift.lat(), lift.lon(), lift.elevation()))
            lift_points = _misc.get_slope(lift_points)
            coords = [[element[1], element[0], int(float(element[2]) * 100 / (2.54 * 12)), element[3]] for element in lift_points]

            feature['geometry']['coordinates'] = coords
            popup_content = f'<h3>{lift.name}</h3>'
            popup_content += f'<p>OSM ID: {lift.lift_id}</p>'
            popup_content += f'<p>Length: {lift.length} ft</p>'
            popup_content += f'<p>Vertical Rise: {lift.vertical} ft</p>'
            if lift.occupancy:
                popup_content += f'<p>Occupancy: {lift.occupancy} people</p>'
            if lift.bubble:
                popup_content += f'<p>&#x2705; Bubble</p>'
            if lift.heated:
                popup_content += f'<p>&#x2705;Heated</p>'
            popup_content += '<form id="delete" class="search-form">'
            popup_content += f'<input type="hidden" name="q" id="q" value="{name}, {state}">'
            popup_content += f'<input type="hidden" name="delete" id="delete_item" value="{lift.lift_id}">'
            popup_content += '<input type="checkbox" id="blacklist" name="blacklist" value=True>'
            popup_content += '<label for="blacklist">Blacklist</label><br>'
            popup_content += '<input class="button-cta" id="delete_submit" type="submit" value="Delete" /></form>'
            feature['properties']['popupContent'] = popup_content
            feature['properties']['label'] = f'{lift.name}'
            
            lon_points = lift.lon()
            lat_points = lift.lat()

            orientation = get_label_orientation(lon_points, lat_points)
            feature['properties']['orientation'] = orientation
            feature['properties']['color'] = 'grey'
            feature['properties']['difficulty_modifier'] = whole_resort_modifier

            geojson['features'].append(feature)

        mountains = database.get_mountains()
        mountains_output = sorted([f'{name}, {state}' for name, state in mountains])
        mountain_index = mountains_output.index(f'{mountain.name}, {mountain.state}')
    if not q:
        mountain = Mountain(None, None)
        mountain.name = ''
        mountain_index = -1

    mountains = database.get_mountains()
    mountains_output = sorted([f'{name}, {state}' for name, state in mountains])

    if mountain_index == len(mountains_output) - 1:
        mountain_index = -1
    
    next_mountain = mountains_output[mountain_index + 1]

    return render_template('management-edit-resort.jinja', nav_links=api.nav_links, management_links=options, active_page='Edit Resort', resorts=mountains_output, mountain=mountain, geojson=geojson, next_mountain=next_mountain)

api.app.run(host='0.0.0.0', port=5000, debug=False)