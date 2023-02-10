# Skelly Synchronize

This package synchronizes a set of videos of the same event by cross-correlating their audio files. The videos will be synchronized so that they all start at the earliest shared time, and end at the latest shared time. 

# How to run

Synchronize your videos by setting the path to your freemocap data folder, your sessionID, and the file types of your videos into __main__.py, then run the file.

## Installation

When this package reaches a point of semi-stable development, it will be pip installable. For now, clone this repository and pip install the `requirements.txt` file.

# Video Requirements

The following requirements must be met for the script to function:

1. Videos must have audio
2. Videos must be in the same file format
3. Videos must have overlapping audio from the same real world event
4. Videos must be in a folder titled "RawVideos", with no other videos in the folder