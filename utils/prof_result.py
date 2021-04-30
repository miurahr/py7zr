import argparse
import pathlib
import pstats
import sys


def print_prof(file):
    p = pstats.Stats(str(file))
    p.strip_dirs()
    p.sort_stats(pstats.SortKey.CUMULATIVE)
    p.print_stats("compressor.py:", 0.1)
    p.print_stats("py7zr.py:", 0.1)
    p.print_stats(0.1)


def main():
    parser = argparse.ArgumentParser(prog='prof_result')
    parser.add_argument('prof', type=pathlib.Path, help='pytest-profile saved prof.')
    args = parser.parse_args()
    print_prof(args.prof)


if __name__ == "__main__":
    sys.exit(main())
