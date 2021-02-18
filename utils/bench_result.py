import argparse
import json
import pathlib
import sys

from tabulate import tabulate  # type: ignore


def read_results_json(results_file) -> dict:
    with open(results_file, 'r') as results:
        root = json.load(results)
    return root


def generate_metainfo(root: dict) -> str:
    machine_info = root['machine_info']
    commit_info = root['commit_info']
    comment_body = 'Machine Info: {} {} [{} {}]\n'.format( machine_info["python_implementation"],
                                                            machine_info["python_version"],
                                                            machine_info["python_compiler"], machine_info["machine"])
    comment_body += 'Commit: {} on {} in {}\n'.format(commit_info['id'], commit_info['branch'], commit_info['time'])
    return comment_body


def get_target(benchmark: dict) -> str:
    return benchmark['params']['name']


def get_rate(bm: dict):
    return bm['extra_info']['rate'] / 1000000


def get_ratio(bm: dict):
    return bm['extra_info']['ratio']


def generate_table(benchmarks: dict, group: str, type='simple') -> str:
    table = []
    for bm in benchmarks:
        if bm['group'] == group:
            table.append([get_target(bm), get_rate(bm), get_ratio(bm), bm['stats']['min'], bm['stats']['max'], bm['stats']['mean']])
    return tabulate(table, headers=['target', 'rate(MB/sec)', 'ratio', 'min(sec)', 'max(sec)', 'mean(sec)'], tablefmt=type)


def generate_comment(root: dict, md=False):
    benchmarks = root['benchmarks']
    if md:
        comment_body = '## Benchmark results\n\n'
        comment_body += generate_metainfo(root)
        comment_body += '\n\n### Compression benchmarks\n\n'
        comment_body += generate_table(benchmarks, 'compress', type='github')
        comment_body += '\n\n### Decompression benchmarks\n\n'
        comment_body += generate_table(benchmarks, 'decompress', type='github')

    else:
        comment_body = 'Benchmark results\n--------------\n\n'
        comment_body += generate_metainfo(root)
        comment_body += '\n\n---- Compression benchmarks\n\n'
        comment_body += generate_table(benchmarks, 'compress')
        comment_body += '\n\n---- Decompression benchmark results\n\n'
        comment_body += generate_table(benchmarks, 'decompress')
    return comment_body


def main():
    parser = argparse.ArgumentParser(prog='benchmark_result')
    parser.add_argument('jsonfile', type=pathlib.Path, help='pytest-benchmark saved result.')
    parser.add_argument('--markdown', action='store_true', help='print markdown')
    args = parser.parse_args()
    body = generate_comment(read_results_json(args.jsonfile), md=args.markdown)
    print(body)


if __name__ == "__main__":
    sys.exit(main())
