kml = input('Paste KML coordinate list: ')
fname = input('Enter filename (without extension): ')
alt = input('Enter altitude (default 30): ') or 30
takeoff = input('Takeoff? (y/n): ') or 'n'

out = "QGC WPL 110\n"


coords = kml.split(' ')

length = len(coords) if takeoff.lower() == 'n' else len(coords) + 1

i=0 
seq = 0
while i < len(coords):
    coord = coords[i].split(',')
    lon = f"{float(coord[0]):.6f}"
    lat = f"{float(coord[1]):.6f}"
    
    if i == 0 and takeoff.lower() == 'y':
        out += f"{seq}\t0\t3\t16\t0\t0\t0\t0\t{lat}\t{lon}\t0\t1\n"
        seq += 1
        out += f"{seq}\t0\t3\t22\t0\t0\t0\t0\t{lat}\t{lon}\t10\t1\n"
    else:
        out += f"{seq}\t0\t3\t16\t0\t0\t0\t0\t{lat}\t{lon}\t{alt}\t1\n"
    
    i += 1
    seq += 1

with open(f"{fname}.txt", 'w') as f:
    f.write(out)
    
    