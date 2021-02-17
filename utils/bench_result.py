import argparse
import json
import pathlib
import sys
from typing import Any, Optional

import texttable  # type: ignore


def read_results_json(results_file) -> dict:
    with open(results_file, 'r') as results:
        root = json.load(results)
    return root


def generate_metainfo(root: dict) -> str:
    machine_info = root['machine_info']
    commit_info = root['commit_info']
    comment_body = 'Benchmark results\n'
    comment_body += '--------------------\n'
    comment_body += 'Machine Info: {} {} [{} {}]\n'.format( machine_info["python_implementation"],
                                                            machine_info["python_version"],
                                                            machine_info["python_compiler"], machine_info["machine"])
    comment_body += 'Commit: {} on {} in {}\n'.format(commit_info['id'], commit_info['branch'], commit_info['time'])
    comment_body += '--------------------\n\n'
    return comment_body


def get_target(benchmark: dict) -> str:
    return benchmark['params']['name']


def get_rate(bm: dict):
    return bm['extra_info']['rate'] / 1000000


def get_ratio(bm: dict):
    return bm['extra_info']['ratio']


def generate_table(benchmarks: dict, group: str) -> str:
    table = texttable.Texttable(max_width=100)
    table.set_deco(texttable.Texttable.HEADER | texttable.Texttable.VLINES)
    table.set_cols_dtype(['t', 'f', 'f', 'f', 'f', 'f'])
    table.set_cols_align(['l', 'r', 'r', 'r', 'r', 'r'])
    table.header(['target', 'rate(MB/sec)', 'ratio', 'min(sec)', 'max(sec)', 'mean(sec)'])
    for bm in benchmarks:
        if bm['group'] == group:
            table.add_row([get_target(bm), get_rate(bm), get_ratio(bm), bm['stats']['min'], bm['stats']['max'], bm['stats']['mean']])
    return table.draw()


def generate_comment(root: dict):
    comment_body = generate_metainfo(root)
    benchmarks = root['benchmarks']
    comment_body += '---- Compression benchmark results\n\n'
    comment_body += generate_table(benchmarks, 'compress')
    comment_body += '\n\n'
    comment_body += '---- Decompression benchmark results\n\n'
    comment_body += generate_table(benchmarks, 'decompress')
    return comment_body


def main():
    parser = argparse.ArgumentParser(prog='benchmark_result')
    parser.add_argument('jsonfile', type=pathlib.Path, nargs=1, help='pytest-benchmark saved result.')
    args = parser.parse_args()
    body = generate_comment(read_results_json(args.jsonf))
    print(body)


if __name__ == "__main__":
    sys.exit(main())
