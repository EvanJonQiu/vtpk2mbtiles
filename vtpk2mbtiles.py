#!/usr/bin/python3
#-*- coding: utf-8 -*-

from pathlib import Path, PurePath
import json
from bitstring import BitArray
from pymbtiles import MBtiles
import gzip
import vector_tile_pb2
from pyproj import Transformer
import argparse

TILE_INDEX_OFFSET = 64
TILE_INDEX_ARRAY_SIZE = 128
TILE_INDEX_RECORD_SIZE = 8

folder_info = []

def get_bundle_offset(bundle_path_name):
  """ Get bundle offset from bundle name
  """
  file_name = PurePath(bundle_path_name).stem
  row = file_name[1:5]
  row_offset = int(row, 16)

  col = file_name[6:10]
  col_offset = int(col, 16)

  return row_offset, col_offset

def get_tile_index_offset(row, column):
  return TILE_INDEX_OFFSET + TILE_INDEX_RECORD_SIZE * (TILE_INDEX_ARRAY_SIZE * (row % TILE_INDEX_ARRAY_SIZE) + (column % TILE_INDEX_ARRAY_SIZE))

def read_record(fd):
  """
  """
  fd.seek(0)
  records = []
  for row in range(TILE_INDEX_ARRAY_SIZE):
    for col in range(TILE_INDEX_ARRAY_SIZE):
      tile_index_offset = get_tile_index_offset(row, col)
      fd.seek(tile_index_offset)
      buffer = fd.read(TILE_INDEX_RECORD_SIZE)
      fd.seek(0)
      [tileOffset, tileSize] = BitArray(buffer).unpack('uintle:40, uintle:24')
      if (tileSize != 0):
        records.append({
          'row': row,
          'column': col,
          'tileOffset': tileOffset,
          'tileSize': tileSize
        })
  return records

def explore_layers(tile_data):
  """ Get layers name from pbf
  """
  uncompressed_tile = gzip.decompress(tile_data)
  tile = vector_tile_pb2.Tile()
  tile.ParseFromString(uncompressed_tile)
  names = []
  for layer in tile.layers:
    names.append(layer.name)

  return names
      
def get_bundles_name(db, folder_info):
  """ Get all bundles name of level
  """
  names = []
  for child in Path(folder_info["path"]).iterdir():
    # get offset from bundle name
    print("processing " + str(child))
    row_offset, col_offset = get_bundle_offset(str(child))

    fd = open(str(child), "rb")
    # read records from a bundle
    records = read_record(fd)
    fd.seek(0)
    for item in records:
      fd.seek(item["tileOffset"])
      tile_data = fd.read(item['tileSize'])
      fd.seek(0)
      row = row_offset + item["row"]
      col = col_offset + item["column"]

      # Flip Y coordinate because MBTiles files are TMS.
      flip_row = (1 << folder_info["level"]) - 1 - row

      # write tile data into MBTiles
      db.write_tile(z=folder_info['level'], x=col, y=flip_row, data=tile_data)
      names.extend(explore_layers(tile_data))
      names = list(set(names))
    
  return names

def get_root(source_folder):
  """ Get object of root.json
  """
  root_file_name = source_folder.joinpath("p12", "root.json")
  f = open(root_file_name, "r")
  content = json.load(f)
  f.close()
  return content

def get_bounds(extent):
  """ transform extent from 3857 to 4326
  """
  bounds = []
  tran = Transformer.from_crs("EPSG:3857", "EPSG:4326")
  temp = [str(x) for x in tran.transform(extent["xmin"], extent["ymin"])]

  temp.reverse()
  bounds.extend(temp)

  temp = [str(x) for x in tran.transform(extent["xmax"], extent["ymax"])]
  temp.reverse()
  bounds.extend(temp)

  return ",".join(bounds)

######################
def main():
  parser = argparse.ArgumentParser(description="convert VTPK to MBTiles")
  parser.add_argument("datapath", type=Path)

  args = parser.parse_args()
  if (not args.datapath):
    exit(-1)

  if (not args.datapath.exists()):
    print(str(args.datapath) + " not exists")
    exit(-1)
  
  tile_dir_path = args.datapath.joinpath("p12", "tile")

  for child in Path(tile_dir_path).iterdir():
    level_name = child.name
    folder_info.append({
      'level': int(level_name[1:]),
      'path': str(child)
    })

  root = get_root(args.datapath)
  mbtiles_name = root["name"] + ".mbtiles"
  db = MBtiles(mbtiles_name, mode="w")

  names = []

  for item in folder_info:
    print("processing level " + str(item["level"]))
    names.extend(get_bundles_name(db, item))
    names = list(set(names))

  ret = []
  for layer in names:
    ret.append({
      "id": layer,
      "fields": {}
    })
  
  vector_layers = {
    "vector_layers": ret
  }

  meta_data = {
    "name": root["name"],
    "format": "pbf",
    "version": root["currentVersion"] or 1,
    "bounds": get_bounds(root["initialExtent"]),
    "minzoom": 0,
    "maxzoom": 16,
    "type": "overlay",
    "json": json.dumps(vector_layers),
    "scheme": "tms"
  }

  # save meta data into MBTiles
  db.meta = meta_data

  db.close()

if __name__ == "__main__":
  main()

