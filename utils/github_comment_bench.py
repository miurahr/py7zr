import argparse
import os
import pathlib

import github
import bench_result as bench


class CommentBenchmark:

    def __init__(self):
        parser = argparse.ArgumentParser(prog='bench_comment_issue')
        parser.add_argument('jsonfile', type=pathlib.Path, help='pytest-benchmark saved result')
        parser.add_argument('repository', help='Repository to post comment')
        parser.add_argument('issue_number', type=int, help='Issue number to post comment')
        parser.add_argument('run_id', help='Run ID of github actions')
        args = parser.parse_args()
        self.jsonfile = args.jsonfile
        self.repository = args.repository
        self.issue_number = args.issue_number
        self.run_id = args.run_id

    def post_comment(self):
        body = bench.generate_comment(self.jsonfile, type='github')
        body += '\n   Posted from [the action](https://github.com/{}/actions/runs/{})\n'.format(self.repository, self.run_id)
        token = os.getenv("GITHUB_TOKEN")
        g = github.Github(token)
        repo = g.get_repo(self.repository)
        issue = repo.get_issue(number=self.issue_number)
        issue.create_comment(body)


if __name__ == "__main__":
    CommentBenchmark().post_comment()
