#!/bin/sh

if [ "${TRAVIS_PULL_REQUEST_BRANCH:-$TRAVIS_BRANCH}" != "master" ]; then
	git checkout origin/master && \
	pytest --benchmark-autosave tests/test_benchmark.py && \
	git checkout ${TRAVIS_COMMIT} && \
	pytest --benchmark-autosave --benchmark-compare --benchmark-compare-fail=min:5% tests/test_benchmark.py
fi