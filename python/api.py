import sqlite3

import misc

db = sqlite3.connect('data/db.db')

cur = db.cursor()

mountain_id = cur.execute('SELECT mountain_id FROM Mountains WHERE name = ? AND state = ?',
                          ('Okemo', 'VT',),).fetchone()[0]

trails = cur.execute(f'SELECT trail_id, name, steepest_50m, gladed FROM Trails WHERE mountain_id = {mountain_id}').fetchall()

json_blob = '{"trails":['
for trail in trails:
    location = cur.execute(f'SELECT lat, lon FROM TrailPoints WHERE trail_id = {trail[0]}').fetchall()
    json_blob += '{"name":"' + trail[1] + '",'.format(trail[1])
    json_blob += '"coords":"{}",'.format(str(location).replace('(', '[').replace(')', ']').replace(' ', ''))
    json_blob += '"color":"' + misc.trail_color(trail[2], trail[3]) + '"},'

json_blob = json_blob[:-1]
json_blob += ']}'

print(json_blob)

db.commit()
db.close()