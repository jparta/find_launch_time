import geopandas as gpd
import geoplot as gplt
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.path import Path
from shapely.geometry import MultiPolygon, Polygon


def kde_ax_from_points(points: gpd.GeoDataFrame, proportion_of_distribution) -> Axes:
    contour_level = 1 - proportion_of_distribution
    levels = [contour_level]
    kde_ax = gplt.kdeplot(points, levels=levels)
    return kde_ax


def kde_gdf_from_points(points: gpd.GeoDataFrame, proportion_of_distribution: float = 0.95) -> gpd.GeoDataFrame:
    # Adapted from https://gist.github.com/haavardaagesen/96f5566a06b83648f393d00a0aa5bd48#file-contours_to_polygons-py
    kde_ax = kde_ax_from_points(points, proportion_of_distribution)

    polygons: list[MultiPolygon] = []
    for col in kde_ax.collections:
        if not isinstance(col, PathCollection):
            continue
        # Loop through all polygons that have the same intensity level
        for contour in col.get_paths():
            if not isinstance(contour, Path):
                continue
            # Create a polygon for the countour
            # First polygon is the main countour, the rest are holes
            for _, poly_points in enumerate(contour.to_polygons()):
                x = poly_points[:,0]
                y = poly_points[:,1]
                poly = Polygon([(i[0], i[1]) for i in zip(x,y)])
                # Append polygon to list
                polygons.append(poly)
    poly_gdf = gpd.GeoDataFrame(geometry=polygons, crs=points.crs)
    return poly_gdf
