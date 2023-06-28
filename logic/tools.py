import geopandas as gpd


def get_single_polygon(gs: gpd.GeoSeries, out_crs=None):
    geoms = gs.geometry
    if len(geoms) == 1:
        the_polygon = geoms[0]
    else:
        the_polygon = gs.unary_union
    if out_crs is None:
        return the_polygon
    else:
        return gpd.GeoDataFrame(geometry=[the_polygon], crs=gs.crs).to_crs(out_crs).geometry.values[0]


def poly_in_crs(poly, in_crs, out_crs):
    return gpd.GeoDataFrame(geometry=[poly], crs=in_crs).to_crs(out_crs).geometry.values[0]
