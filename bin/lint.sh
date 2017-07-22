#!/bin/bash

# Return the same exit status as pylint
set -e
source "$(dirname "$(readlink -e "$0")")/head.sh"
"${VIRTUALENV}/bin/pylint" --rcfile=src/.pylintrc src "$@"

