import requests, json, time, ftplib

node_url = "http://localhost:6869"
out = requests.get(f'{node_url}/blocks/height').json()
height = out['height']
f = open("height.txt", "w+")
try:
    f.write(str(height))
finally:
    f.close()
session = ftplib.FTP('host','user','passwd')
session.cwd('/public_html/')
with open("height.txt", 'rb') as contents:
    session.storlines("STOR height.txt", contents)
session.quit()



