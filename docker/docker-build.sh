#!/usr/bin/env bash

# Go to the "main" directory
cd ..

VERSION=$(python ./utilities/find_version.py)
echo "Detected version: $VERSION"

echo "Building..."
docker build -t nano:$VERSION . --build-arg VERSION=$VERSION
echo "DONE!"
