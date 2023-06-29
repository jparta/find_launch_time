# Imports gevent, which does monkey patching. Import this first to avoid
# troubles with other imports.
from astra.simulator import flight, forecastEnvironment

import json
import logging
import tempfile
import typing
from datetime import datetime, timedelta
from pathlib import Path
from pprint import pformat, pprint

import geopandas as gpd
from matplotlib import pyplot as plt
import numpy as np
import requests

from proportion_of_kde import get_proportion_of_built_area_in_kde
from kde_tools import kde_gdf_from_points


logging.basicConfig(level=logging.DEBUG)


days_to_launch = 1
launch_datetime = datetime.now() + timedelta(days=days_to_launch)


def make_launch_params(latitude: float, longitude: float):
    elevation_dataset = "FABDEM"
    elevation_url = (
        f"https://api.elevationapi.com/api/Elevation?lat={latitude}&lon={longitude}&dataSet={elevation_dataset}"
    )
    response = requests.get(elevation_url)
    elevation = response.json()["geoPoints"][0]["elevation"]
    return {
        "launchSiteLat": latitude,
        "launchSiteLon": longitude,
        "launchSiteElev": elevation,
        "launchTime": launch_datetime,
        "inflationTemperature": 10,
        "forceNonHD": False,
    }


def make_flight_params(
    balloon: str,
    nozzle_lift_kg: float,
    payload_train_weight_kg: float,
    parachute: str,
    number_of_sim_runs: int,
    train_equiv_sphere_diam: float,
    output_path: Path,
    output_formats: tuple[str],
    debugging: bool = False,
):
    return {
        "balloonGasType": "gt96He",
        "balloonModel": balloon,
        "nozzleLift": nozzle_lift_kg,
        "payloadTrainWeight": payload_train_weight_kg,
        "parachuteModel": parachute,
        "numberOfSimRuns": number_of_sim_runs,
        "trainEquivSphereDiam": train_equiv_sphere_diam,
        "outputPath": output_path,
        "outputFormats": output_formats,
        "debugging": debugging,
        "log_to_file": True,
    }


def run_sims():
    launch_coords_possibilities = {
        "Kartanonrannan_koulu": (60.153144, 24.551671),
        "Vantinlaakso": (60.184101, 24.623690)
    }
    launch_coords = launch_coords_possibilities["Vantinlaakso"]
    flight_train_mass_kg = 0.604
    flight_train_equiv_sphere_diam = 0.285
    sim_runs = 5
    balloon = "SFB800"
    nozzle_lift_kg = 1.6
    parachute = "SFP800"

    output_dir = tempfile.TemporaryDirectory()
    output_path = Path(output_dir.name) / 'astra_out'
    output_formats = ('json',)
    launch_params = make_launch_params(*launch_coords)
    flight_params = make_flight_params(
        balloon=balloon,
        nozzle_lift_kg=nozzle_lift_kg,
        payload_train_weight_kg=flight_train_mass_kg,
        parachute=parachute,
        number_of_sim_runs=sim_runs,
        train_equiv_sphere_diam=flight_train_equiv_sphere_diam,
        output_path=output_path,
        output_formats=output_formats,
        debugging=False,
    )
    print(f"launch params: {pformat(launch_params)}")
    print(f"flight params: {pformat(flight_params)}")
    sim_environment = forecastEnvironment(**launch_params)
    the_flight = flight(
        **flight_params,
        environment=sim_environment,
    )
    the_flight.run()
    predicted_landing_sites = get_predicted_landing_sites(output_path / "out.json")
    return predicted_landing_sites


def get_predicted_landing_sites(astra_flight_json_filepath: Path):
    with open(astra_flight_json_filepath) as f:
        flight_data = json.load(f)
    landing_markers = flight_data["landingMarkers"]
    lats = [marker["lat"] for marker in landing_markers]
    lons = [marker["lon"] for marker in landing_markers]
    predicted_landing_sites = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(lons, lats), crs="EPSG:4326"
    )
    return predicted_landing_sites


def main():
    predicted_landing_sites = run_sims()
    proportion_of_built_area = get_proportion_of_built_area_in_kde(predicted_landing_sites)
    print(f"proportion of built area: {proportion_of_built_area}")


if __name__ == "__main__":
    main()
