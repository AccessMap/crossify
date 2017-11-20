import geopandas as gpd
from shapely.geometry import LineString


def make_links(st_crossings, offset=1):
    crs = st_crossings.crs

    links = []
    for idx, row in st_crossings.iterrows():
        geom = row.geometry
        if geom.length > (2 * offset):
            first = geom.interpolate(offset)
            last = geom.interpolate(geom.length - offset)

            sw1 = LineString([geom.coords[0], first])
            sw2 = LineString([geom.coords[-1], last])
            new_geom = LineString([first, last])

            for link in [sw1, sw2]:
                links.append({
                    'geometry': link,
                    'highway': 'footway',
                    'footway': 'sidewalk',
                    'layer': row['layer']
                })
            st_crossings.loc[idx, 'geometry'] = new_geom

    sw_links = gpd.GeoDataFrame(links)

    sw_links.crs = crs
    st_crossings.crs = crs

    return st_crossings, sw_links
