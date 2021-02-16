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


def pytest_benchmark_group_stats(config, benchmarks, group_by):
    result = {}
    for bench in benchmarks:
        s = bench['name'].split('_')
        if len(s) == 4 and s[2] == 'filters':
            groupname = s[3].split('[')[0]
        else:
            groupname = 'others'
        group = result.setdefault("%s: %s" % (groupname, bench['group']), [])
        group.append(bench)
    return sorted(result.items())


# Remove parametrization data from JSON output to keep it to a reasonable size
def pytest_benchmark_update_json(config, benchmarks, output_json):
    for benchmark in output_json['benchmarks']:
        if 'data' in benchmark['params']:
            benchmark['params'].pop('data')
        if 'data' in benchmark['stats']:
            benchmark['stats'].pop('data')
        if benchmark['extra_info'].get('data_size', None) is not None:
            rate = benchmark['extra_info'].get('data_size', None) / benchmark['stats']['mean']
            benchmark['extra_info']['rate'] = rate
