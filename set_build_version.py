import json, io, sys

p = r'.build\server.json'
d = json.load(io.open(p, encoding='utf-8'))
d['version'] = sys.argv[1]
d['desc'] = d['desc'].replace('v2.1.0', 'v' + sys.argv[1])
io.open(p, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
print(d['version'], d['serviceId'], d['workDir'], d['port'])
