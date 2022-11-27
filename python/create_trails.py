from collections import Counter


def process_trails(ways):
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
                if tag['piste type'] == 'downhill':
                    way['type'] = 'trail'
                elif tag['piste type'] == 'yes':
                    print('Way #{} ({}) is marked as piste type "yes". Please make more specific.'.format(
                        way['id'], way['name']))
                    way['type'] = 'trail'
                else:
                    way['type'] = None

            # check if the way is a lift
            if 'aerialway' in tag:
                if tag['aerialway'] in ['goods', 'station', 'zip line', 'explosive', 'abandoned', 'pylon', 'disused', 'proposed', 'no']:
                    way['type'] = None
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
            if 'mtb scale imba' in tag:
                way['type'] = None
            if 'landuse' in tag:
                if tag['landuse'] == 'grass':
                    way['type'] = None
            if 'natural' in tag:
                if tag['natural'] == 'wood':
                    way['area'] = True
                    way['gladed'] = True
                if tag['natural'] == 'grassland':
                    way['type'] = None
            if 'leaf type' in tag:
                if way['gladed'] != False:
                    way['gladed'] = True
                way['area'] = True
            if 'public_transport' in tag:
                if 'platform' in tag['public_transport']:
                    way['type'] = None
        # if way['name'] != None and way['type'] == 'trail':
        #    if 'glade' in way['name'] or 'Glade' in way['name'] or 'Tree Skiing' in way['name']:
        #        if way['gladed'] == None:
        #            way['gladed'] = True
        #            print('Way #{} ({}) was found to be a glade through its name. Please double check & add the necessary tags.'.format(
        #                way['id'], way['name']))

        if way['type'] != None:
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
            print(item)
            for trail in trails:
                if trail['name'] == item[0]:
                    print(trail['id'])

    return (trails, lifts)
