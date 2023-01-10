from collections import Counter


def process_trails(ways: list(dict)) -> tuple(list(dict), list(dict)):
    trails = []
    lifts = []
    for unprocessed_way in ways:
        way = {
            'id': unprocessed_way['id'],
            'name': None,
            'official_rating': None,
            'gladed': None,
            'area': None,
            'type': None,
            'valid': True,
            'nodes': unprocessed_way['nodes']
        }
        for tag in unprocessed_way['tags']:
            # name
            if 'name' in tag:
                way['name'] = tag['name']

            # check if the way can be a trail
            if 'piste difficulty' in tag:
                way['official_rating'] = tag['piste difficulty']
                way['type'] = 'trail'
            if 'piste type' in tag:
                if tag['piste type'] == 'downhill' or tag['piste type'] == 'traverse':
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

            # exceptions
            if 'piste grooming' in tag:
                if 'skating' in tag['piste grooming']:
                    way['type'] = None
                    way['valid'] = False
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
            if 'public_transport' in tag:
                if 'platform' in tag['public_transport']:
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

        if way['type'] != None and way['valid']:
            if way['name'] == None or way['name'] == '':
                way['name'] = ''
                print(
                    'Way #{} has no name. Please add a name.'.format(way['id']))
            if way['type'] == 'trail':
                if way['gladed'] == None:
                    way['gladed'] = False
                if way['area'] == None:
                    way['area'] = False
                trails.append({key: way[key] for key in [
                    'id', 'name', 'official_rating', 'gladed', 'area', 'nodes']})
            if way['type'] == 'lift':
                lifts.append({key: way[key]
                             for key in ['id', 'name', 'nodes']})

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
