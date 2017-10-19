from crossify import cross
import geopandas as gpd

# Read files
sidewalks = gpd.read_file('../crossify-testdata/udistrict_sidewalks.geojson')
streets = gpd.read_file('../crossify-testdata/udistrict_streets.geojson')

# Ensure only lines remain
sidewalks = sidewalks[sidewalks.geometry.type == 'LineString']
streets = streets[streets.geometry.type == 'LineString']

# Reproject to NAD83 in meters (WA)
sidewalks = sidewalks.to_crs({'init': 'epsg:26910'})
streets = streets.to_crs({'init': 'epsg:26910'})

# Create crossings (this is sloooooooooow)
crossings = cross.make_graph(sidewalks, streets)['crossings']

# Add OSM-ie metadata. Questionably useful at this stage
crossings_final = gpd.GeoDataFrame(crossings.geometry)
crossings_final['highway'] = 'footway'
crossings_final['footway'] = 'crossing'
crossings_final['crossing'] = 'unmarked'

# Reproject to WGS84
crossings_final.crs = sidewalks.crs
crossings_final = crossings_final.to_crs({'init': 'epsg:4326'})

crossings_final.to_file('./crossings.geojson', driver='GeoJSON')
