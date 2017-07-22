#!/bin/bash

# Return the same exit status as tox.
set -e
source "$(dirname "$(readlink -e "$0")")/head.sh"
"${VIRTUALENV}/bin/tox" -e py27 "$@"

