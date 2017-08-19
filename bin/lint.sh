#!/bin/bash

# Return the same exit status as pylint
set -e
source "$(dirname "$(readlink -e "$0")")/head.sh"
"${VIRTUALENV}/bin/pylint" --rcfile=src/.pylintrc src "$@"

# We set -e, so if we make it this far then the lint must have passed.
echo "10/10, would lint again."

