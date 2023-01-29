@echo off

:: Create Necessary Directories
mkdir data
mkdir data\cached
mkdir data\osm
mkdir static\maps
mkdir static\thumbnails

:: Set the name of the text file
set "filename=data\secret.py"

:: Generate a random string
set "string=This is a unique string that should be changed by the end user"

:: Create the text file and add the string to it
echo secret = '%string%' > %filename%
