import argparse
import json
import pathlib
import sys

from tabulate import tabulate  # type: ignore


def generate_metainfo(root: dict) -> str:
    machine_info = root['machine_info']
    commit_info = root['commit_info']
    result = 'Machine: {} {} on {}({})\n'.format(machine_info['system'], machine_info['release'],
                                                 machine_info['cpu']['brand'],
                                                 machine_info['cpu']['hz_actual_friendly'])
    result += 'Python: {} {} [{} {}]\n'.format(machine_info["python_implementation"],
                                               machine_info["python_version"],
                                               machine_info["python_compiler"], machine_info["machine"])
    result += 'Commit: {} on {} in {}\n'.format(commit_info['id'], commit_info['branch'], commit_info['time'])
    return result


def generate_table(benchmarks: dict, group: str, type='simple') -> str:
    table = []
    for bm in benchmarks:
        if group == bm['group']:
            target = bm['params']['name']
            rate = bm['extra_info']['rate'] / 1000000
            ratio = bm['extra_info']['ratio']
            min = bm['stats']['min']
            max = bm['stats']['max']
            avr = bm['stats']['mean']
            table.append([target, rate, ratio, min, max, avr])
    return tabulate(table, headers=['target', 'rate(MB/sec)', 'ratio', 'min(sec)', 'max(sec)', 'mean(sec)'],
                    tablefmt=type)


def generate_comment(results_file, type):
    with open(results_file, 'r') as results:
        root = json.load(results)
    benchmarks = root['benchmarks']
    comment_body = '## Benchmark results\n\n'
    comment_body += generate_metainfo(root)
    comment_body += '\n\n### Compression benchmarks\n\n'
    comment_body += generate_table(benchmarks, 'compress', type=type)
    comment_body += '\n\n### Decompression benchmarks\n\n'
    comment_body += generate_table(benchmarks, 'decompress', type=type)
    return comment_body


def main():
    parser = argparse.ArgumentParser(prog='benchmark_result')
    parser.add_argument('jsonfile', type=pathlib.Path, help='pytest-benchmark saved result.')
    parser.add_argument('--markdown', action='store_true', help='print markdown table')
    args = parser.parse_args()
    if args.markdown:
        type = 'github'
    else:
        type = 'simple'
    body = generate_comment(args.jsonfile, type)
    print(body)


if __name__ == "__main__":
    sys.exit(main())
