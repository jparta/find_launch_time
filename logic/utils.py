import geopandas as gpd
from matplotlib import pyplot as plt

from config import max_built_area_proportion, human_crs


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


def plot_kde_and_built_area(kde_poly_gs, built_area_gs, proportion_of_built_area_to_whole, points=None):
    if proportion_of_built_area_to_whole < max_built_area_proportion:
        built_area_color = 'green'
    else:
        built_area_color = 'red'
    kde_ax = kde_poly_gs.to_crs(human_crs).plot(alpha=0.5, figsize=(10, 10))
    if built_area_gs is not None:
        # intersection exists
        built_area_gs.to_crs(human_crs).plot(ax=kde_ax, color=built_area_color)
    if points is not None:
        points.to_crs(human_crs).plot(ax=kde_ax, color='black', markersize=1)
    proportion_in_chart = round(proportion_of_built_area_to_whole*100, 1)
    proportion_text = f"{proportion_in_chart} %"
    plt.text(0.8, 0.2, proportion_text, transform=kde_ax.transAxes)
    plt.show()
