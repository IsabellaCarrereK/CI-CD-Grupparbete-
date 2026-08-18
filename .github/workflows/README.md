# CI Workflow

`ci.yml` defines the GitHub Actions continuous-integration pipeline for this repository.

It runs on:

- every `push`
- every `pull_request`

The job:

1. checks out the repository
2. installs Python 3.11
3. installs the project and development dependencies
4. runs Ruff linting
5. runs pytest

A successful run should be green before a feature branch is merged into `main`.

This directly supports the DE25 assignment requirement that each pull request trigger automated linting/tests before merge.
