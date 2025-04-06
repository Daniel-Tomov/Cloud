#!/bin/bash

# Define the port to check (e.g., HAProxy frontend port)
PORT=5432

# Check if HAProxy is running
if ! pidof haproxy > /dev/null; then
    echo "HAProxy is not running"
    exit 1
fi

# Check if HAProxy is listening on the expected port
if ! ss -ltn | grep -q ":${PORT}"; then
    echo "HAProxy is not listening on port ${PORT}"
    exit 2
fi

# All checks passed
exit 0