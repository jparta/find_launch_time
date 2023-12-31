import os
from datetime import datetime, timezone
from pprint import pprint

os.environ['USE_PYGEOS'] = '0'

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from .config import processing_crs, human_crs, bbox
from .proportion_of_kde import get_enhanced_ensemble_outputs
from .load_data import DataLoader


def get_sampled_points(count, mean, crs, cov=None) -> gpd.GeoDataFrame:
    if cov is None:
        cov = [[6e6, 4e6], [4e6, 3.5e6]]
    # cov = np.array([[6, -3], [-3, 3.5]])
    points = np.random.multivariate_normal(mean, cov, size=count)
    points_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(points[:, 0], points[:, 1]), crs=crs)
    return points_gdf

def get_means(data_loader: DataLoader, n=1):
    # random points in Finland
    dist_mean_points: list[Point] = []
    finland_polygon = data_loader.finland_polygon

    while len(dist_mean_points) < n:
        # generate random point in Finland
        x = np.random.uniform(bbox[0], bbox[2])
        y = np.random.uniform(bbox[1], bbox[3])
        point = Point(x, y)
        if finland_polygon.contains(point):
            dist_mean_points.append(point)
    return dist_mean_points


def how_close_points_are_in_polygon(gdf):
    # gdf = gdf.to_crs(processing_crs)
    polygon = gdf.geometry.values[0]
    points = polygon.exterior.coords
    distances = []
    for i in range(len(points) - 1):
        j = i + 1
        point_1 = Point(points[i])
        point_2 = Point(points[j])
        distance = point_1.distance(point_2)
        distances.append(distance)
    return np.mean(distances)


def main():
    count_samples = 10000
    data_loader = DataLoader()
    means = get_means(data_loader=data_loader)
    for mean in means:
        mean_point = Point(mean.x, mean.y)
        mean_in_processing_crs = gpd.GeoDataFrame(geometry=[mean_point], crs=human_crs).to_crs(processing_crs).geometry.values[0].coords[0]
        points = get_sampled_points(count_samples, mean_in_processing_crs, processing_crs)
        outputs = get_enhanced_ensemble_outputs(
            launch_time=datetime.now(timezone.utc),
            points_gdf=points,
            data_loader=data_loader
        )
        proportion_of_bad_landing = outputs.proportion_of_bad_landing_to_kde
        print(f"proportion of bad landing: {proportion_of_bad_landing}")
        pprint({key: str(val)[:50] for key, val in outputs.to_dict().items()})

if __name__ == '__main__':
    main()
