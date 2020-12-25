# vtpk2mbtiles
Convert VTPK to MBTiles. VTPK have to decompress before convert.

## Reference source
* openvtpk(https://github.com/syncpoint/openvtpk)

## How to run
```powershell
python vtpk2mbtiles.py VTPK_PATH
```
VTPK_PATH is the folder where is VTPK decompressed to

## Vector tile specification
* vector tile document(https://github.com/mapbox/vector-tile-spec)

## Dependencies
* bitstring(https://bitstring.readthedocs.org)
* pymbtiles(https://github.com/consbio/pymbtiles)
* pyproj(https://github.com/pyproj4/pyproj)