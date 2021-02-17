import argparse
import os
import pathlib

import github
import bench_result as bench


def post_comment(jsonfile, token: str, repository: str, issue_number:int):
    body = bench.generate_comment(bench.read_results_json(jsonfile))
    g = github.Github(token)
    repo = g.get_repo(repository)
    issue = repo.get_issue(number=issue_number)
    issue.create_comment(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='bench_comment_issue')
    parser.add_argument('jsonfile', type=pathlib.Path, nargs=1, help='pytest-benchmark saved result.')
    args = parser.parse_args()
    jsonfile = args.jsonfile
    token = os.getenv("GITHUB_TOKEN")
    repository = os.getenv("REPOSITORY")
    issue_number = int(os.getenv("ISSUE"))
    post_comment(jsonfile, token, repository, issue_number)
