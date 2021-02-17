import argparse
import os
import pathlib

from PyGithub import github
import bench_result as bench


def post_comment(jsonfile, token, repository, issue_number):
    body = bench.generate_comment(bench.read_results_json(jsonfile))
    g = github(token)
    repo = g.get_repo(repository)
    issue = repo.get_issue(number=issue_number)
    issue.create_comment(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='bench_comment_issue')
    parser.add_argument('jsonfile', type=pathlib.Path)
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    repository = os.getenv("REPOSITORY")
    issue_number = os.getenv("ISSUE")
    post_comment(args.jsonfile, token, repository, issue_number)
