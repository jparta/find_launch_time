import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

from config import human_crs, processing_crs, built_area_tags, geofabrik_osm_column_types, bbox


data_location = Path(__file__).parent.parent / "data"


def apply_tag_conditions(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    conditions = None
    for key, val in built_area_tags:
        if key not in gdf.columns:
            continue
        cond = gdf[key] == val
        if conditions is None:
            conditions = cond
        else:
            conditions = conditions | cond
    if conditions is None:
        return gdf
    print(gdf[conditions])

    relevant_gdf = gdf[conditions]
    return relevant_gdf


def heal_geometry(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf_fixed = gdf.buffer(0)
    # gdf_fixed = gdf.make_valid()
    return gpd.GeoDataFrame(gdf, geometry=gdf_fixed, crs=gdf.crs)


def pare_gdf_to_essentials(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # set more efficient dtypes
    for column, dtype in geofabrik_osm_column_types.items():
        if column in gdf.columns:
            gdf[column] = gdf[column].astype(dtype)
    gdf = apply_tag_conditions(gdf)
    # limit to only the columns we need
    """
    osm_keys = list(set(a for a, b in built_area_tags))
    other_columns_to_keep = ['name', 'table_name', 'geom', 'geometry']
    columns_to_keep = osm_keys + other_columns_to_keep
    print(f"Head of gdf before limiting columns:\n{gdf.head()}")
    columns_to_drop = [column for column in gdf.columns if column not in columns_to_keep]
    gdf = gdf.drop(columns_to_drop, axis=1)

    # we're only interested in built areas, i.e. columns of interest are not null
    if all(key in gdf.columns for key in osm_keys):
        print(f"Head of gdf before dropping nulls:\n{gdf.head()}, length: {len(gdf)}")
        gdf = gdf[gdf[osm_keys].notnull().any(axis=1)]
        print(f"Head of gdf after dropping nulls:\n{gdf.head()}, length: {len(gdf)}")
    """

    return gdf


def clip_geometry_to_bbox(gdf: gpd.GeoDataFrame, bbox: tuple, bbox_crs: str) -> gpd.GeoDataFrame:
    shared_crs = processing_crs
    bbox_polygon = box(*bbox)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox_polygon], crs=bbox_crs).to_crs(shared_crs)
    bbox_gdf_bounds = tuple(bbox_gdf.total_bounds)
    bbox_edge_lengths = (bbox_gdf_bounds[2] - bbox_gdf_bounds[0], bbox_gdf_bounds[3] - bbox_gdf_bounds[1])
    bbox_length = max(bbox_edge_lengths)
    buffer_by = 1 * bbox_length
    bbox_gdf = bbox_gdf.buffer(buffer_by)
    bbox_xy = tuple(bbox_gdf.total_bounds)
    print(f"bbox_xy: {bbox_xy}")

    clipped_gdf = gdf.to_crs(shared_crs).cx[bbox_xy[0]:bbox_xy[2], bbox_xy[1]:bbox_xy[3]]
    # finland_osm_gdf = gpd.GeoDataFrame(geometry=finland_osm_fix)
    geometry_info(clipped_gdf)
    print("Clipped geometry")
    return clipped_gdf


def top_polygons_by_area_info(gdf: gpd.GeoDataFrame, n: int = 10) -> list[float]:
    # add area column
    gdf = gdf.to_crs(processing_crs)
    gdf['m^2_area'] = gdf.area
    top_polygons = gdf.sort_values(by='m^2_area', ascending=False).head(n)
    return top_polygons


def geometry_info(gdf: gpd.GeoDataFrame):
    # print(f"gs.head():\n{gdf.head()}")
    top_polys = top_polygons_by_area_info(gdf)
    show_columns = ['name', 'm^2_area', 'geometry']
    show_columns_filtered = [column for column in show_columns if column in top_polys.columns]
    cant_show = set(show_columns) - set(show_columns_filtered)
    if cant_show:
        print(f"won't show columns: {set(show_columns) - set(show_columns_filtered)}, because they're not in gdf.columns")
    print(f"top names and areas:\n{top_polys[show_columns_filtered]}")


def load_osm_built_area_data() -> gpd.GeoSeries:
    finland_osm_filepath = data_location / "finland.sqlite"
    finland_filepath = data_location / "finland_osm.feather"
    helsinki_filepath = data_location / "helsinki_osm.feather"

    if Path(finland_filepath).is_file():
        gdf = gpd.read_feather(finland_filepath)
        finland_osm_gdf = pare_gdf_to_essentials(gdf)
    else:
        con = sqlite3.connect(finland_osm_filepath)
        finland_osm_df = pd.DataFrame()
        geom_types = ['multipolygons', 'other_relations']
        for geom_type in geom_types:
            print(f"Processing '{geom_type}'...")
            df = pd.read_sql(f"SELECT *, '{geom_type}' AS table_name FROM {geom_type};", con)
            finland_osm_df = pd.concat([finland_osm_df, df], ignore_index=True)
        # convert dataframe into geodataframe
        print("Creating geometry column")
        finland_osm_df['geometry'] = gpd.GeoSeries.from_wkt(finland_osm_df['WKT_GEOMETRY'])
        finland_osm_gdf = gpd.GeoDataFrame(finland_osm_df, crs=human_crs)
        finland_osm_gdf = pare_gdf_to_essentials(finland_osm_gdf)
        finland_osm_gdf = heal_geometry(finland_osm_gdf)
        geometry_info(finland_osm_gdf)
        finland_osm_gdf.to_feather(finland_filepath)

    use_clipped_area = False
    if not use_clipped_area:
        output_gs = finland_osm_gdf["geometry"]
    elif Path(helsinki_filepath).is_file():
        print("Loading helsinki feather")
        helsinki_gdf = gpd.read_feather(helsinki_filepath)
        helsinki_pared_gdf = pare_gdf_to_essentials(helsinki_gdf)
        output_gs = helsinki_pared_gdf["geometry"]
        # geometry_info(finland_osm_gs)
        print("Loaded helsinki feather")
    else:
        print("Loading Finland feather")
        gdf = gpd.read_feather(finland_filepath)
        finland_osm_gdf = pare_gdf_to_essentials(gdf)
        print("Loaded Finland feather")
        geometry_info(finland_osm_gdf)
        helsinki_pared_gdf = clip_geometry_to_bbox(finland_osm_gdf, bbox, bbox_crs=human_crs)
        helsinki_pared_gdf.to_feather(helsinki_filepath)
        output_gs = helsinki_pared_gdf["geometry"]
    print("finland_osm_gs.info():")
    print(output_gs.info(verbose=True, memory_usage='deep'))
    if not isinstance(output_gs, gpd.GeoSeries):
        raise TypeError(f"finland_osm_gs is not a GeoSeries, it is a {type(output_gs)}")
    print("Loaded OSM data, returning from load_osm_built_area_data()")
    return output_gs


def get_finland_polygon() -> Polygon:
    # Load Finland as a polygon
    admin_0_countries_filepath = data_location / "ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
    world = gpd.read_file(admin_0_countries_filepath)
    finland_polygon = world[world.ADMIN == "Finland"].geometry.values[0]
    return finland_polygon
