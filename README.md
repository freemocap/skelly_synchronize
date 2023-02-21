# Skelly Synchronize

This package synchronizes a set of videos of the same event by cross-correlating their audio files. The videos will be synchronized so that they all start at the earliest shared time, and end at the latest shared time. 

# How to run

Synchronize your videos by setting the path to your freemocap data folder, your sessionID, and the file types of your videos into __main__.py, then run the file. The sessionID should be the name of a subfolder of your freemocap data folder, and should contain a subfolder called `RawVideos` containing the videos that need synching.

![Main](https://user-images.githubusercontent.com/24758117/220470598-580360ef-8d4f-447c-820e-cc4d2d544c07.png)

The terminal output while running should look like this:

<img width="1250" alt="TerminalOutput" src="https://user-images.githubusercontent.com/24758117/220470626-c3592b65-6d8f-439b-87e7-20b83d6aff0f.png">

A `SyncedVideos` folder will be created in the session folder and filled with the synchronized video files. The session folder will also have an `AudioFiles` folder containing audio files of the raw videos, which are used in processing.

<img width="626" alt="FileStructureAfterRunning" src="https://user-images.githubusercontent.com/24758117/220470692-2f573367-1737-4842-b23e-e6fb79b1e4c8.png">

## Installation

When this package reaches a point of semi-stable development, it will be pip installable. For now, clone this repository and pip install the `requirements.txt` file.

# Video Requirements

The following requirements must be met for the script to function:

1. Videos must have audio
2. Videos must be in the same file format
3. Videos must have overlapping audio from the same real world event
4. Videos must be in a folder titled "RawVideos", with no other videos in the folder

# Expected File Structure

To function correctly, Skelly Synchronize expects the following folder structure:
```
freemocap_data_folder:
    sessionID:
        RawVideos:
            Cam0.mp4
            Cam1.mp4
            ...
    ...
```
The camera names can be changed, and the file format may changed as well, although freemocap currently only uses `.mp4`.
