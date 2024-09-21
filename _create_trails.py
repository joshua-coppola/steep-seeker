from collections import Counter


def process_trails(ways: list(dict())) -> tuple():
    trails = []
    lifts = []
    for unprocessed_way in ways:
        way = {
            'id': unprocessed_way['id'],
            'name': None,
            'official_rating': None,
            'gladed': None,
            'ungroomed': False,
            'area': None,
            'occupancy': None,
            'capacity': None,
            'duration': None,
            'detachable': None,
            'bubble': None,
            'heated': None,
            'type': None,
            'valid': True,
            'nodes': unprocessed_way['nodes']
        }
        for tag in unprocessed_way['tags']:
            # name
            if 'name' in tag:
                way['name'] = tag['name']
                if 'tubing' in way['name'] or 'Tubing' in way['name']:
                    way['type'] = None
                    way['valid'] = False

            if 'piste name' in tag:
                way['name'] = tag['piste name']

            # check if the way can be a trail
            if 'piste difficulty' in tag:
                way['official_rating'] = tag['piste difficulty']
                way['type'] = 'trail'
            if 'piste type' in tag:
                if tag['piste type'] == 'downhill' or tag['piste type'] == 'traverse' or tag['piste type'] == 'snow park':
                    way['type'] = 'trail'
                elif tag['piste type'] == 'yes':
                    print('Way #{} ({}) is marked as piste type "yes". Please make more specific.'.format(
                        way['id'], way['name']))
                    way['type'] = 'trail'
                else:
                    way['type'] = None
                    way['valid'] = False

            # check if the way is a lift
            if 'aerialway' in tag:
                if tag['aerialway'] in ['goods', 'station', 'zip line', 'explosive', 'abandoned', 'pylon', 'disused', 'proposed', 'no']:
                    way['type'] = None
                    way['valid'] = False
                else:
                    way['type'] = 'lift'

            # gladed
            if 'gladed' in tag:
                if tag['gladed'] == 'yes' and way['gladed'] != False:
                    way['gladed'] = True
                if tag['gladed'] == 'no':
                    way['gladed'] = False

            # area
            if 'area' in tag:
                if tag['area'] == 'yes':
                    way['area'] = True
                else:
                    way['area'] = False

            # groomed
            if 'piste grooming' in tag:
                # filter out nordic trails
                if 'skating' in tag['piste grooming'] or 'scooter' in tag['piste grooming']:
                    way['type'] = None
                    way['valid'] = False
                if 'backcountry' in tag['piste grooming'] or 'mogul' in tag['piste grooming'] or 'no' in tag['piste grooming']:
                    way['ungroomed'] = True

            # lift tags
            if 'aerialway occupancy' in tag:
                way['occupancy'] = int(tag['aerialway occupancy'])

            if 'aerialway capacity' in tag:
                way['capacity'] = int(tag['aerialway capacity'])
                if way['capacity'] < 100:
                    way['capacity'] = None

            if 'aerialway duration' in tag:
                way['duration'] = tag['aerialway duration']
                if ' ' in way['duration']:
                    time = way['duration'].split(' ')
                    if len(time) == 2:
                        minutes = time[0]
                        seconds = time[1]
                    elif len(time) == 3 and time[0] == '0':
                        minutes = time[1]
                        seconds = time[2]
                    minutes = int(minutes)
                    seconds = int(seconds)
                    way['duration'] = round(minutes + (seconds / 60), 1)
                way['duration'] = float(way['duration'])

            if 'aerialway detachable' in tag:
                if tag['aerialway detachable'] == 'yes':
                    way['detachable'] = True
                else:
                    way['detachable'] = False

            if 'aerialway bubble' in tag:
                if tag['aerialway bubble'] == 'yes':
                    way['bubble'] = True
                else:
                    way['bubble'] = False

            if 'aerialway heated' in tag:
                if tag['aerialway heated'] == 'yes':
                    way['heated'] = True
                else:
                    way['heated'] = False
                    

            # exceptions
            if 'mtb scale imba' in tag:
                way['type'] = None
                way['valid'] = False
            if 'landuse' in tag:
                if tag['landuse'] == 'grass':
                    way['type'] = None
                    way['valid'] = False
            if 'natural' in tag:
                if tag['natural'] == 'wood':
                    way['area'] = True
                    way['gladed'] = True
                if tag['natural'] == 'grassland':
                    way['type'] = None
                    way['valid'] = False
            if 'leaf type' in tag:
                if way['gladed'] != False:
                    way['gladed'] = True
                way['area'] = True
            if 'public transport' in tag:
                if 'platform' in tag['public transport']:
                    way['type'] = None
                    way['valid'] = False
            if 'name' in tag:
                if 'closed' in tag['name'].lower():
                    way['type'] = None
                    way['valid'] = False
                if 'bike trail' in tag['name'].lower():
                    way['type'] = None
                    way['valid'] = False
            if 'disused' in tag:
                way['type'] = None
                way['valid'] = False
            if 'abandoned' in tag:
                way['type'] = None
                way['valid'] = False

        if way['type'] != None and way['valid']:
            if way['name'] == None or way['name'] == '':
                way['name'] = ''
                print(
                    'Way #{} has no name. Please add a name.'.format(way['id']))
            way['name'] = way['name'].replace(' amp ', ' & ')
            way['name'] = way['name'].replace(' quot ', ' " ')
            way['name'] = way['name'].replace(' lt ', ' < ')
            way['name'] = way['name'].replace(' gt ', ' > ')

            if way['type'] == 'trail':
                if way['gladed'] == None:
                    way['gladed'] = False
                if way['area'] == None:
                    way['area'] = False
                if way['gladed'] == True:
                    way['ungroomed'] = False
                trails.append({key: way[key] for key in [
                    'id', 'name', 'official_rating', 'gladed', 'ungroomed', 'area', 'nodes']})
            if way['type'] == 'lift':
                lifts.append({key: way[key]
                             for key in ['id', 'name', 'occupancy', 'capacity', 'duration', 'detachable', 'bubble', 'heated', 'nodes']})

    trails = merge_trails(trails)

    counts = Counter([trail['name'] for trail in trails])
    multiples = set()
    for trail in trails:
        if counts[trail['name']] > 1:
            multiples.add((trail['name'], counts[trail['name']]))
    if len(multiples) > 0:
        print('The following trails have X number of ways named the same. Please see if they all make sense.')
        for item in multiples:
            if item[0] == '':
                continue
            print(item)
            for trail in trails:
                if trail['name'] == item[0]:
                    print(trail['id'])

    return (trails, lifts)


def merge_trails(trails):
    def find_indices(list_to_check, item_to_find):
        indices = []
        for idx, value in enumerate(list_to_check):
            if value == item_to_find:
                indices.append(idx)
        return indices
    previously_seen_names = []
    previously_seen_dicts = []

    for i, trail in enumerate(trails):
        trail_merged = False
        previous_merge = None
        if trail['name'] in previously_seen_names:
            indices = find_indices(previously_seen_names, trail['name'])
            for j in indices:
                if previously_seen_dicts[j] == None:
                    continue
                common_traits = 1
                if previously_seen_dicts[j]['official_rating'] == trail['official_rating']:
                    common_traits += 1
                if previously_seen_dicts[j]['gladed'] == trail['gladed']:
                    common_traits += 1
                if previously_seen_dicts[j]['ungroomed'] == trail['ungroomed']:
                    common_traits += 1
                if previously_seen_dicts[j]['area'] == trail['area']:
                    common_traits += 1
                if common_traits == 5:
                    # check if previously seen trail connects to top of current trail
                    if previously_seen_dicts[j]['nodes'][-1]['lat'] == trail['nodes'][0]['lat'] and previously_seen_dicts[j]['nodes'][-1]['lon'] == trail['nodes'][0]['lon']:
                        new_nodes = previously_seen_dicts[j]['nodes'] + trail['nodes']
                        previously_seen_dicts[j]['nodes'] = new_nodes
                        trails[i]['nodes'] = new_nodes
                        if trail_merged:
                            previously_seen_dicts[previous_merge] = None
                            indices = find_indices(previously_seen_names, trail['name'])
                        trail_merged = True
                        previous_merge = j
                        
                    # check if currently seen trail connects to a previous trail
                    if previously_seen_dicts[j]['nodes'][0]['lat'] == trail['nodes'][-1]['lat'] and previously_seen_dicts[j]['nodes'][0]['lon'] == trail['nodes'][-1]['lon']:
                        new_nodes = trail['nodes'] + previously_seen_dicts[j]['nodes']
                        previously_seen_dicts[j]['nodes'] = new_nodes
                        trails[i]['nodes'] = new_nodes
                        if trail_merged:
                            previously_seen_dicts[previous_merge] = None
                            indices = find_indices(previously_seen_names, trail['name'])
                        trail_merged = True
                        previous_merge = j

        if not trail_merged:
            previously_seen_names.append(trail['name'])
            previously_seen_dicts.append(trail)

    output_trails = []
    for trail in previously_seen_dicts:
        if trail != None:
            output_trails.append(trail)

    return output_trails
