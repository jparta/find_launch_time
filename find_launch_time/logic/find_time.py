# Imports gevent, which does monkey patching. Import this first to avoid
# troubles with other imports.
import dataclasses
from astra.simulator import flight, forecastEnvironment

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pprint import pformat, pprint

os.environ['USE_PYGEOS'] = '0'

import geopandas as gpd
import requests
from requests.adapters import HTTPAdapter, Retry

from .load_data import DataLoader
from .proportion_of_kde import EnhancedEnsembleOutputs, get_enhanced_ensemble_outputs


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def make_launch_params(
    latitude: float,
    longitude: float,
    launch_time: datetime,
    session: requests.Session,
):
    elevation_dataset = "FABDEM"
    elevation_url = (
        f"https://api.elevationapi.com/api/Elevation?lat={latitude}&lon={longitude}&dataSet={elevation_dataset}"
    )
    response = session.get(elevation_url)
    elevation = response.json()["geoPoints"][0]["elevation"]
    return {
        "launchSiteLat": latitude,
        "launchSiteLon": longitude,
        "launchSiteElev": elevation,
        "launchTime": launch_time,
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


def make_output_path():
    output_dir = tempfile.TemporaryDirectory()
    output_path = Path(output_dir.name) / 'astra_out'
    return output_path


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


def run_sims(
    launch_time: datetime,
    sim_runs: int,
    output_path: Path,
    debug: bool,
    session: requests.Session,
):
    launch_coords_possibilities = {
        "Kartanonrannan_koulu": (60.153144, 24.551671),
        "Vantinlaakso": (60.184101, 24.623690)
    }
    launch_coords = launch_coords_possibilities["Vantinlaakso"]
    flight_train_mass_kg = 0.604
    flight_train_equiv_sphere_diam = 0.285
    balloon = "SFB800"
    nozzle_lift_kg = 1.6
    parachute = "SFP800"

    output_formats = ('json',)
    launch_params = make_launch_params(*launch_coords, launch_time, session)
    flight_params = make_flight_params(
        balloon=balloon,
        nozzle_lift_kg=nozzle_lift_kg,
        payload_train_weight_kg=flight_train_mass_kg,
        parachute=parachute,
        number_of_sim_runs=sim_runs,
        train_equiv_sphere_diam=flight_train_equiv_sphere_diam,
        output_path=output_path,
        output_formats=output_formats,
        debugging=debug,
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


class FindTime:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.data_loader = DataLoader()
        if debug:
            logger.setLevel(logging.DEBUG)
        self.reqsession = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        self.reqsession.mount('http://', HTTPAdapter(max_retries=retries))
        self.reqsession.mount('https://', HTTPAdapter(max_retries=retries))

    def get_prediction_geometries(
        self,
        prediction_window_length: timedelta,
        launch_time_increment: timedelta,
        launch_time_min: datetime=datetime.now(timezone.utc),
        sims_per_launch_time: int=2,
    ):
        """Get the geometries of the predicted landing sites for the next 10 days."""
        launch_time_max = launch_time_min + prediction_window_length
        launch_time = launch_time_min
        while launch_time <= launch_time_max:
            output_path = make_output_path()
            run_sims(
                launch_time,
                sims_per_launch_time,
                output_path,
                self.debug,
                self.reqsession
            )
            predicted_landing_sites = get_predicted_landing_sites(output_path / "out.json")
            enhanced_outputs = get_enhanced_ensemble_outputs(
                launch_time=launch_time,
                points_gdf=predicted_landing_sites,
                data_loader=self.data_loader,
            )
            print(f"proportion of bad landing area: {enhanced_outputs.proportion_of_bad_landing_to_kde}")
            yield enhanced_outputs
            launch_time = launch_time + launch_time_increment

    def refresh_data(self):
        self.data_loader.refresh_data()


if __name__ == "__main__":
    time_finder = FindTime(debug=True)
    time_finder.get_prediction_geometries(
        prediction_window_length=timedelta(days=10),
        launch_time_increment=timedelta(days=1),
    )
