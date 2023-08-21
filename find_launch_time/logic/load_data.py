import logging
import shutil
import sqlite3
from pathlib import Path
import subprocess
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd
import pyrosm
import requests
from shapely.geometry import Polygon, box

from .config import human_crs, processing_crs, bad_landing_tags, geofabrik_osm_column_types


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


data_location = Path(__file__).parent.parent / "data"
def init_data_dir():
    data_location.mkdir(exist_ok=True)
init_data_dir()

data_files = {
    "admin_0_countries_zip_filepath" : data_location / "ne_110m_admin_0_countries.zip",
    "admin_0_countries_unzipped_filepath": data_location / "ne_110m_admin_0_countries",
    "admin_0_countries_shp_filepath": data_location / "ne_110m_admin_0_countries" / "ne_110m_admin_0_countries.shp",
    "osm_pbf": None,
    "osm_sqlite": data_location / "osm.sqlite",
    "osm_feather": data_location / "osm.feather",
}

data_files_needed = [
    "admin_0_countries_shp_filepath",
    "osm_feather",
]


def apply_tag_conditions(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    conditions = None
    for key, val in bad_landing_tags:
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


def log_sqlite_table_size(sqlite_filepath: Path, table_name: str):
    conn = sqlite3.connect(sqlite_filepath)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    logger.info(f"table {table_name} has {cursor.fetchone()[0]} rows")


def wipe_data():
    try:
        shutil.rmtree(data_location)
    except FileNotFoundError:
        pass


def data_ready() -> bool:
    for data_file in data_files_needed:
        filepath_raw = data_files[data_file]
        if filepath_raw is None:
            return False
        filepath_obj = Path(filepath_raw)
        if not filepath_obj.exists():
            return False
    return True


def download_and_unzip_countries():
    countries_110m_url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    countries_110m_zip_filepath = data_files["admin_0_countries_zip_filepath"]
    if countries_110m_zip_filepath.exists():
        logger.info(f"countries shapefile already downloaded to {countries_110m_zip_filepath}")
        return
    resp = requests.get(countries_110m_url)
    resp.raise_for_status()
    with open(countries_110m_zip_filepath, 'wb') as f:
        f.write(resp.content)
    destination = data_files["admin_0_countries_unzipped_filepath"]
    with ZipFile(countries_110m_zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(destination)
    logger.info(f"Got countries shapefile from {countries_110m_url} and unzipped to {destination}")


def sqlite_to_geodataframe(sqlite_filepath: Path) -> gpd.GeoDataFrame:
    logger.info(f"converting sqlite file {sqlite_filepath} to geodataframe")
    con = sqlite3.connect(sqlite_filepath)
    geometries_of_interest = pd.DataFrame()
    geom_types = ['multipolygons', 'other_relations']
    for geom_type in geom_types:
        print(f"Processing '{geom_type}'...")
        df = pd.read_sql(f"SELECT *, '{geom_type}' AS table_name FROM {geom_type};", con)
        geometries_of_interest = pd.concat([geometries_of_interest, df], ignore_index=True)
    # convert dataframe into geodataframe
    print("Creating geometry column")
    geometries_of_interest['geometry'] = gpd.GeoSeries.from_wkt(geometries_of_interest['WKT_GEOMETRY'])
    geometries_of_interest = gpd.GeoDataFrame(geometries_of_interest, crs=human_crs)
    geometries_of_interest = pare_gdf_to_essentials(geometries_of_interest)
    geometries_of_interest = heal_geometry(geometries_of_interest)
    log_sqlite_table_size(sqlite_filepath, 'multipolygons')
    logger.info(f"geometry_info(geometries_of_interest): {geometry_info(geometries_of_interest)}")
    return geometries_of_interest


def get_osm_in_feather_form():
    osm_pbf_filepath = data_files['osm_pbf']
    if not (osm_pbf_filepath and Path(osm_pbf_filepath).exists()):
        osm_pbf_filepath = pyrosm.get_data("Finland", directory=data_location, update=True)
        data_files['osm_pbf'] = osm_pbf_filepath
        logger.info(f"Downloaded osm_pbf to {osm_pbf_filepath}")
    else:
        logger.info(f"Using existing osm_pbf_filepath: {osm_pbf_filepath}")
    # convert to sqlite using ogr2ogr
    osm_sqlite_filepath = data_files['osm_sqlite']
    command = f"ogr2ogr -f SQLite -lco FORMAT=WKT {osm_sqlite_filepath} {osm_pbf_filepath}"
    logger.info(f"converting osm pbf file to sqlite")
    subprocess.run(command.split())
    geometries_of_interest = sqlite_to_geodataframe(osm_sqlite_filepath)
    geometries_of_interest.to_feather(data_files['osm_feather'])
    logger.info(f"Converted {osm_pbf_filepath} to {data_files['osm_feather']}")


def download_and_prepare_data():
    download_and_unzip_countries()
    get_osm_in_feather_form()
    if not data_ready():
        raise RuntimeError("Data not ready even though it should be.")


def load_osm_bad_landing_data() -> gpd.GeoSeries:
    if not data_ready():
        logger.info("Data not ready. Getting files now")
        download_and_prepare_data()
        logger.info("Data ready")
    osm_feather_filepath = data_files['osm_feather']

    gdf = gpd.read_feather(osm_feather_filepath)
    for column, dtype in geofabrik_osm_column_types.items():
        if column in gdf.columns:
            gdf[column] = gdf[column].astype(dtype)

    output_gs = gdf["geometry"]
    print("finland_osm_gs.info():")
    print(output_gs.info(verbose=True, memory_usage='deep'))
    if not isinstance(output_gs, gpd.GeoSeries):
        raise TypeError(f"finland_osm_gs is not a GeoSeries, it is a {type(output_gs)}")
    print("Loaded OSM data")
    return output_gs


def get_finland_polygon() -> Polygon:
    if not data_ready():
        logger.info("Data not ready. Getting files now")
        download_and_prepare_data()
        logger.info("Data ready")
    # Load Finland as a polygon
    admin_0_countries_filepath = data_files['admin_0_countries_shp_filepath']
    world = gpd.read_file(admin_0_countries_filepath)
    finland_polygon = world[world.ADMIN == "Finland"].geometry.values[0]
    return finland_polygon


class DataLoader:
    def __init__(self, debug: bool = False) -> None:
        self.bad_landing_sindex_by_crs = {}
        init_data_dir()
        self.load_data()
        if debug:
            logger.setLevel(logging.DEBUG)

    def save_bad_landing_sindex(self, crs):
        if crs in self.bad_landing_sindex_by_crs:
            return
        sindex = self.bad_landing_gs.to_crs(crs).sindex
        self.bad_landing_sindex_by_crs[crs] = sindex

    def load_data(self):
        self.bad_landing_gs = load_osm_bad_landing_data().to_crs(processing_crs)
        sindex_crs = {processing_crs}
        # Initialize spatial index
        for crs in sindex_crs:
            self.save_bad_landing_sindex(crs)
        self.finland_polygon = get_finland_polygon()

    def get_bad_landing_sindex(self, crs) -> gpd.GeoSeries:
        if crs not in self.bad_landing_sindex_by_crs:
            self.save_bad_landing_sindex(crs)
        return self.bad_landing_sindex_by_crs[crs]

    def refresh_data(self):
        wipe_data()
        init_data_dir()
        self.load_data()

