import argparse
import os
import pathlib

import github
import bench_result as bench


def post_comment(jsonfile: pathlib.Path, repository: str, issue_number:int):
    body = bench.generate_comment(bench.read_results_json(jsonfile))
    token = os.getenv("GITHUB_TOKEN")
    g = github.Github(token)
    repo = g.get_repo(repository)
    issue = repo.get_issue(number=issue_number)
    issue.create_comment(body)


def parse():
    parser = argparse.ArgumentParser(prog='bench_comment_issue')
    parser.add_argument('jsonfile', type=pathlib.Path, nargs=1, help='pytest-benchmark saved result.')
    parser.add_argument('repository', type=str, nargs=1, help='Repository to post comment')
    parser.add_argument('issue_number', type=int, nargs=1, help='Issue number to post comment')
    args = parser.parse_args()
    jsonfile = args.jsonfile
    repository = args.repository
    issue_number = args.issue_number
    return jsonfile, repository, issue_number


if __name__ == "__main__":
    jsonfile, repository, issue_number = parse()
    post_comment(jsonfile, repository, issue_number)
