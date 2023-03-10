# Skelly Synchronize

This package synchronizes a set of videos of the same event by cross-correlating their audio files. The videos will be synchronized so that they all start at the earliest shared time, and end at the latest shared time. 

# Install and Run

Skelly_synchronize can be installed through pip by running `pip install skelly_synchronize` in your terminal. Once it has installed, it can be run with the command `python -m skelly_synchronize`. While running, the GUI window may appear frozen, but the terminal should show the progress. Large videos may take a significant amount of time. 

<img width="593" alt="Skelly_synchronize_gui_window" src="https://user-images.githubusercontent.com/24758117/221995127-340899d7-4f04-4f87-a2d7-ba1d49cd00e2.png">

# Video Requirements

The following requirements must be met for the script to function:

1. Videos must have audio
2. Videos must be in the same file format (default is ".mp4")
3. All videos in folder must have overlapping audio from the same real world event


# How to run from source

First clone this repository and pip install the `requirements.txt` file.

Synchronize your videos by setting the path to your folder of raw videos and the file types of your videos into `skelly_synchronize.py`, lines 343-344, then run the file. 

<img width="559" alt="skelly_synchronize_main_function" src="https://user-images.githubusercontent.com/24758117/221996311-07dab11f-0104-4407-b921-40cd364b39bc.png">

The terminal output while running should look like this:

<img width="1250" alt="TerminalOutput" src="https://user-images.githubusercontent.com/24758117/221996277-a925c457-205c-411d-aaaa-eda7ca774fed.png">

A `SyncedVideos` folder will be created in the session folder and filled with the synchronized video files. The session folder will also have an `AudioFiles` folder containing audio files of the raw videos, which are used in processing.

<img width="626" alt="FileStructureAfterRunning" src="https://user-images.githubusercontent.com/24758117/220470692-2f573367-1737-4842-b23e-e6fb79b1e4c8.png">
