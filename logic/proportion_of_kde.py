import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PolyPatch

from config import processing_crs, human_crs
from load_data import load_osm_built_area_data
from tools import get_single_polygon, poly_in_crs



def intersecting_built_area(kde_poly_gs, built_area_gs):
    shared_crs = processing_crs
    kde_multipoly = get_single_polygon(kde_poly_gs, out_crs=shared_crs)
    print(f"number of vertices: {len(kde_multipoly.exterior.coords)}")
    built_area_poly = get_single_polygon(built_area_gs, out_crs=shared_crs)
    print(f"built_area_poly bounds: {poly_in_crs(built_area_poly, shared_crs, human_crs).bounds}")
    print(f"kde_multipoly bounds: {poly_in_crs(kde_multipoly, shared_crs, human_crs).bounds}")
    # plot both geoseries
    fig, ax = plt.subplots()
    kde_poly_gs.plot(ax=ax, color='red')
    built_area_gs.plot(ax=ax, color='blue')
    # plt.show()
    if not kde_multipoly.intersects(built_area_poly):
        return None
    intersection_poly = kde_multipoly.intersection(built_area_poly)
    intersection_gdf = gpd.GeoDataFrame(geometry=[intersection_poly], crs=kde_poly_gs.crs)
    intersection_gdf.plot()
    plt.show()
    return intersection_gdf


def get_proportion_of_built_area_in_kde(kde_poly_gdf):
    built_area_gs: gpd.GeoSeries = load_osm_built_area_data()
    built_area_gs = built_area_gs.to_crs(processing_crs)
    built_area_intersecting_with_kde = intersecting_built_area(kde_poly_gdf, built_area_gs)
    proportion_of_built_area_to_whole = (built_area_intersecting_with_kde.area.sum() / kde_poly_gdf.area.sum()
                                         if built_area_intersecting_with_kde is not None else 0)
    return proportion_of_built_area_to_whole
