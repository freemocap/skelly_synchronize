# Skelly Synchronize

This package synchronizes a set of videos of the same event by cross-correlating their audio files. The videos will be synchronized so that they all start at the earliest shared time, and end at the latest shared time. 

# Install and Run

Skelly_synchronize can be installed through pip by running `pip install skelly_synchronize` in your terminal. Once it has installed, it can be run with the command `python -m skelly_synchronize`.

# Video Requirements

The following requirements must be met for the script to function:

1. Videos must have audio
2. Videos must be in the same file format (default is ".mp4")
3. All videos in folder must have overlapping audio from the same real world event


# How to run from source

First clone this repository and pip install the `requirements.txt` file.

Synchronize your videos by setting the path to your folder of raw videos and the file types of your videos into `skelly_synchronize.py`, lines 343-344, then run the file. 

![Main](https://user-images.githubusercontent.com/24758117/220470598-580360ef-8d4f-447c-820e-cc4d2d544c07.png)

The terminal output while running should look like this:

<img width="1250" alt="TerminalOutput" src="https://user-images.githubusercontent.com/24758117/220470626-c3592b65-6d8f-439b-87e7-20b83d6aff0f.png">

A `SyncedVideos` folder will be created in the session folder and filled with the synchronized video files. The session folder will also have an `AudioFiles` folder containing audio files of the raw videos, which are used in processing.

<img width="626" alt="FileStructureAfterRunning" src="https://user-images.githubusercontent.com/24758117/220470692-2f573367-1737-4842-b23e-e6fb79b1e4c8.png">
