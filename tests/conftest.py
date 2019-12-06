# Configuration for pytest to automatically collect types.
# Thanks to Guilherme Salgado.
import os

import pytest
from pyannotate_runtime import collect_types


def pytest_collection_finish(session):
    """Handle the pytest collection finish hook: configure pyannotate.
    Explicitly delay importing `collect_types` until all tests have
    been collected.  This gives gevent a chance to monkey patch the
    world before importing pyannotate.
    """
    collect_types.init_types_collection()


@pytest.fixture(autouse=True)
def collect_types_fixture():
    collect_types.start()
    yield
    collect_types.stop()


def pytest_sessionfinish(session, exitstatus):
    os.makedirs('build/', exist_ok=True)
    collect_types.dump_stats("build/type_info.json")
