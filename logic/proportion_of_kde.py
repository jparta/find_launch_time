import geopandas as gpd
from matplotlib import pyplot as plt

from config import processing_crs, human_crs
from kde_tools import kde_gdf_from_points
from load_data import load_osm_bad_landing_data
from utils import get_single_geometry, poly_in_crs, plot_kde_and_bad_landing_polys


def bad_landing_intersecting_with_kde(kde_poly_gs, bad_landing_gs):
    shared_crs = processing_crs
    kde_geometry = get_single_geometry(kde_poly_gs, out_crs=shared_crs)
    print(f"number of vertices: {len(kde_geometry.exterior.coords)}")
    bad_landing_geometry = get_single_geometry(bad_landing_gs, out_crs=shared_crs)
    print(f"bad landing geometry bounds: {poly_in_crs(bad_landing_geometry, shared_crs, human_crs).bounds}")
    print(f"kde geometry bounds: {poly_in_crs(kde_geometry, shared_crs, human_crs).bounds}")
    if not kde_geometry.intersects(bad_landing_geometry):
        return None
    intersection_poly = kde_geometry.intersection(bad_landing_geometry)
    intersection_gdf = gpd.GeoDataFrame(geometry=[intersection_poly], crs=shared_crs)
    return intersection_gdf


def get_proportion_of_bad_landing_in_kde(points_gdf):
    shared_crs = processing_crs
    kde_poly_gdf = kde_gdf_from_points(points_gdf).to_crs(shared_crs)
    bad_landing_gs: gpd.GeoSeries = load_osm_bad_landing_data()
    bad_landing_in_kde = bad_landing_intersecting_with_kde(kde_poly_gdf, bad_landing_gs)
    proportion_of_bad_landing_to_whole = (bad_landing_in_kde.to_crs(shared_crs).area.sum() / kde_poly_gdf.area.sum()
                                         if bad_landing_in_kde is not None else 0)
    plot_kde_and_bad_landing_polys(
        kde_poly_gdf,
        bad_landing_in_kde,
        proportion_of_bad_landing_to_whole,
        points=points_gdf
    )
    return proportion_of_bad_landing_to_whole
