from crossify import cross
import geopandas as gpd

sidewalks = gpd.read_file('../mapathon-data-staging/inputdata/sidewalks.shp')
streets = gpd.read_file('../mapathon-data-staging/inputdata/streets.shp')

crossings = cross.make_graph(sidewalks, streets)['crossings']

crossings.to_file('./crossings.shp')
