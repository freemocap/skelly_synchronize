# Skelly Synchronize

Skelly Synchronize is a package for synchronizing videos post-recording, without the need for timestamps. There are multiple options for synchronizing videos, including cross correlation of the audio files and contrast checking of the video brightness. The videos will be synchronized so that they all start at the earliest shared time, and end at the latest shared time. 

# Install and Run

Skelly_synchronize can be installed through pip by running `pip install skelly_synchronize` in your terminal. Once it has installed, it can be run with the command `python -m skelly_synchronize`. 

While running, the GUI window may appear frozen, but the terminal should show the progress. Large videos may take a significant amount of time. 

Skelly_synchronize currently depends on FFmpeg, a command line tool that handles the video files. If you do not have FFmpeg downloaded, you will need to install it separately. You can download FFmpeg here: https://ffmpeg.org/download.html

<img width="598" alt="Screen Shot 2023-10-10 at 9 51 11 AM" src="https://github.com/freemocap/skelly_synchronize/assets/24758117/2c34a076-90d9-4d8f-bd3a-5b4649586d8c">


# Using Skelly Synchronize

Once you have the GUI open, choose a folder of raw videos that you would like to synchronize. The videos must overlap in time to be able to be synchronized. The software currently works with `mp4`, `mkv`, `avi`, `mpeg`, and `mov` files. Once the folder of videos has been selected, you can press the button for the synchronization method you would like to run. The synchronized videos will be placed in a folder called "synchronized_videos" that will be in the same directory as the folder of raw videos.

For **audio synchronization**, videos must all have audio tracks. Synchronization will work better if there are short, distinct sounds audible from each camera, for example a loud clap.

For **brightness synchronization**, there must be a quick increase in brightness across all of the video files. This method requires a significant brightness change visible to all cameras, for example turning on a bright light or firing a flash visible to all cameras. The synchronization will be based off of the first brightness change in each video that crosses a threshold. You can set the brightness ratio threshold in the gui before synchronizing. The threshold takes into account both the brightness contrast compared to the preceding frame, and the rate of change of brightness contrast. It may take multiple tries with different brightness ratio thresholds to get proper synchronization, although the default should work in most cases.

## Additional Files

Skelly synchronize will create a variety of additional files during synchronization, depending on what synchronization method is used and what preprocessing steps are required for your videos.

Two debug files will always be created. The first, `debug_plot.png`, shows a visualization of the videos pre and post synchronization to give visual confirmation of the synchronization process. The second, `synchronization_debug.toml`, gives information on both the raw and synchronized videos, and provides the lag dictionary, which shows the offsets in seconds between the start of each raw video and the first moment all videos recorded.

Videos that do not have the same framerate (and audio files that do not have the same sample rate) will be normalized to have matching framerates, which will create a "normalized_videos" folder inside of the raw videos folder that has normalized copies of the original videos. 

Audio synchronization will place the extracted audio files into the synchronized video folder. Brightness synching will place numpy files containing the brightness of the videos across time in both the raw and synchronized video folders.
