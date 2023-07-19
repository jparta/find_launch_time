import geopandas as gpd
from matplotlib import pyplot as plt

from shapely import geometry

from .config import max_bad_landing_proportion, human_crs


def get_single_geometry(gs: gpd.GeoSeries, out_crs=None) -> geometry.base.BaseGeometry:
    the_polygon = gs.unary_union
    if out_crs is None:
        return the_polygon
    else:
        return gpd.GeoDataFrame(geometry=[the_polygon], crs=gs.crs).to_crs(out_crs).geometry.values[0]


def poly_in_crs(poly, in_crs, out_crs):
    return gpd.GeoDataFrame(geometry=[poly], crs=in_crs).to_crs(out_crs).geometry.values[0]


def plot_kde_and_bad_landing_polys(kde_poly_gs, bad_landing_gs, proportion_of_bad_landing_to_kde, points=None):
    plotting_crs = human_crs
    kde_poly_gs = kde_poly_gs.to_crs(plotting_crs)
    if bad_landing_gs is not None:
        bad_landing_gs = bad_landing_gs.to_crs(plotting_crs)
    if proportion_of_bad_landing_to_kde < max_bad_landing_proportion:
        bad_landing_color = 'green'
    else:
        bad_landing_color = 'red'
    kde_ax = kde_poly_gs.plot(alpha=0.5, figsize=(10, 10))
    if bad_landing_gs is not None:
        # intersection exists
        bad_landing_gs.plot(ax=kde_ax, color=bad_landing_color)
    if points is not None:
        points.to_crs(human_crs).plot(ax=kde_ax, color='black', markersize=1)
    proportion_in_chart = round(proportion_of_bad_landing_to_kde*100, 1)
    proportion_text = f"{proportion_in_chart} %"
    plt.text(0.8, 0.2, proportion_text, transform=kde_ax.transAxes)
    plt.show()
