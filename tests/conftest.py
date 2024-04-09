# Configuration for pytest.
# Thanks to Guilherme Salgado.

import shutil

import cpuinfo
import pytest

from py7zr import unpack_7zarchive


@pytest.fixture(scope="session")
def register_shutil_unpack_format():
    shutil.register_unpack_format("7zip", [".7z"], unpack_7zarchive)


def pytest_benchmark_update_json(config, benchmarks, output_json):
    """Calculate compression/decompression speed and add as extra_info"""
    for benchmark in output_json["benchmarks"]:
        if "data_size" in benchmark["extra_info"]:
            rate = benchmark["extra_info"].get("data_size", 0.0) / benchmark["stats"]["mean"]
            benchmark["extra_info"]["rate"] = rate


def pytest_benchmark_update_machine_info(config, machine_info):
    cpu_info = cpuinfo.get_cpu_info()
    brand = cpu_info.get("brand_raw", None)
    if brand is None:
        brand = "{} core(s) {} CPU ".format(cpu_info.get("count", "unknown"), cpu_info.get("arch", "unknown"))
    machine_info["cpu"]["brand"] = brand
    machine_info["cpu"]["hz_actual_friendly"] = cpu_info.get("hz_actual_friendly", "unknown")


def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true", default=False, help="run slow tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        # --run-slow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
