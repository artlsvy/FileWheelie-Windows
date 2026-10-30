#!/bin/sh
# Container build plus single-file portable/user-installer and optional DEB.
set -eu
cd "$(dirname "$0")/.."
exec python3 packaging/linux/build.py "$@"
