import dataclasses
from datetime import datetime
from pprint import pprint
import geopandas as gpd
from dataclasses import dataclass

from .config import processing_crs, human_crs
from .kde_tools import kde_gdf_from_points
from .load_data import DataLoader
from .utils import get_single_geometry, poly_in_crs


@dataclass
class EnhancedEnsembleOutputs:
    """The outputs of the sims, enhanced by KDE computation and comparison with bad landing polygons."""
    launch_time: datetime
    bad_landing_areas: gpd.GeoDataFrame | None
    predicted_landing_sites: gpd.GeoDataFrame
    kde: gpd.GeoDataFrame
    proportion_of_bad_landing_to_kde: float

    def to_dict(self):
        naive_dict = dataclasses.asdict(self)
        # Use GeoJSON format for the geometries
        final_format_dict = {}
        for key, value in naive_dict.items():
            if isinstance(value, gpd.GeoDataFrame):
                final_format_dict[key] = value.to_json()
            else:
                final_format_dict[key] = value
        return final_format_dict


def bad_landing_intersecting_with_kde(kde_poly_gs, data_loader: DataLoader):
    kde_simplify_tolerance = 10  # meters
    kde_geometry = get_single_geometry(kde_poly_gs, out_crs=processing_crs)
    simplified_kde_geometry = kde_geometry.simplify(kde_simplify_tolerance)
    # print(f"number of vertices: {len(kde_geometry.exterior.coords)}")
    # bad_landing_geometry = get_single_geometry(bad_landing_gs, out_crs=shared_crs)
    # print(f"bad landing geometry bounds: {poly_in_crs(bad_landing_geometry, shared_crs, human_crs).bounds}")
    # print(f"kde geometry bounds: {poly_in_crs(simplified_kde_geometry, processing_crs, human_crs).bounds}")
    bad_landing_sindex = data_loader.get_bad_landing_sindex(processing_crs)
    intersecting = bad_landing_sindex.query(simplified_kde_geometry, predicate="intersects")
    if not intersecting.size:
        return None
    intersection_gs = data_loader.bad_landing_gs.to_crs(processing_crs).iloc[intersecting].intersection(kde_geometry)
    return intersection_gs


def get_enhanced_ensemble_outputs(launch_time: datetime, points_gdf, data_loader: DataLoader) -> EnhancedEnsembleOutputs:
    """Generate a Kernel Density Estimate (KDE) from the estimated landing location points,
    and compare it with the bad landing polygons. Return the whole package of outputs,
    including the points passed to this function, their KDE, the proportion of bad landing area to KDE area,
    and the bad landing polys within the KDE.
    """
    shared_crs = processing_crs
    kde = kde_gdf_from_points(points_gdf).to_crs(shared_crs)
    bad_landing_in_kde = bad_landing_intersecting_with_kde(kde, data_loader)
    proportion_of_bad_landing_to_whole = (bad_landing_in_kde.to_crs(shared_crs).area.sum() / kde.area.sum()
                                         if bad_landing_in_kde is not None else 0)
    """
    plot_kde_and_bad_landing_polys(
        kde_gdf,
        bad_landing_in_kde,
        proportion_of_bad_landing_to_whole,
        points=points_gdf
    )
    """
    if (not isinstance(bad_landing_in_kde, (gpd.GeoDataFrame, gpd.GeoSeries, type(None)))
        or not isinstance(kde, (gpd.GeoDataFrame, gpd.GeoSeries))):
        error_string = f"""\
            bad_landing_in_kde and kde_gdf type requirements not met,
            got {type(bad_landing_in_kde)} and {type(kde)}
        """
        raise ValueError(error_string)
    enhanced_outputs = EnhancedEnsembleOutputs(
        launch_time=launch_time,
        bad_landing_areas=bad_landing_in_kde,
        predicted_landing_sites=points_gdf,
        kde=kde,
        proportion_of_bad_landing_to_kde=proportion_of_bad_landing_to_whole
    )
    return enhanced_outputs
