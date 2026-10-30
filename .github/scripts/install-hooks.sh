#!/bin/sh
# Turn on the repo's git hooks (.githooks/): pre-commit runs the repo lint,
# pre-push runs the unit tests and dry runs. Once per clone:
#   sh .github/scripts/install-hooks.sh
cd "$(dirname "$0")/../.." || exit 1
chmod +x .githooks/*
git config core.hooksPath .githooks && echo "git hooks enabled (core.hooksPath = .githooks)"
