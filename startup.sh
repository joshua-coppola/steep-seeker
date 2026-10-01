#!/bin/bash

# Create Necessary Directories
mkdir data
mkdir data/cached
mkdir data/osm
mkdir static/maps
mkdir static/thumbnails

# Set the name of the text file
filename="data/secret.py"

# Generate a random string
string=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)

# Create the text file and add the string to it
echo "secret = '$string'" > "$filename"
