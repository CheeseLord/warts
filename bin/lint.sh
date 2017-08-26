#!/bin/bash

# Return the same exit status as pylint
set -e
source "$(dirname "$(readlink -e "$0")")/head.sh"
"${VIRTUALENV}/bin/pylint" --rcfile=src/.pylintrc src "$@"

# We set -e, so if we make it this far then the lint must have passed.
# But if there were command line arguments, then we may be running in quiet
# mode, so to be safe, skip this message.
if (( $# == 0 )); then
    echo "10/10, would lint again."
fi

