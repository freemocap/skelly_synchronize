# Skelly Synchronize

Skelly Synchronize is a package for synchronizing videos post-recording, without the need for timestamps. There are multiple options for synchronizing videos, including cross correlation of the audio files and contrast checking of the video brightness. The videos will be synchronized so that they all start at the earliest shared time, and end at the latest shared time. 

## Install and Run

Skelly Synchronize is a Python library (`core`), a FastAPI server (`api`), and a React web UI (`frontend`), plus a CLI. To use the web UI, run the API server and the frontend dev server as two processes:

```
pip install -e ".[api]"
skelly-sync-api
```

This starts the API on `http://127.0.0.1:8000`. Then, in a second terminal:

```
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`) in your browser. See [`frontend/README.md`](frontend/README.md) for details.

Skelly_synchronize currently depends on FFmpeg, a command line tool that handles the video files. If you do not have FFmpeg downloaded, you will need to install it separately. You can download FFmpeg here: https://ffmpeg.org/download.html

## Using Skelly Synchronize

Once you have the web UI open, choose a folder of raw videos that you would like to synchronize. The videos must overlap in time to be able to be synchronized. The software currently works with `mp4`, `mkv`, `avi`, `mpeg`, and `mov` files. Once the folder of videos has been selected, you can choose the synchronization method you would like to run. The synchronized videos will be placed in a folder called "synchronized_videos" that will be in the same directory as the folder of raw videos (or in a custom output folder, if one was specified).

### Synchronization Methods

**Audio Cross Correlation** synchronizes by aligning the audio files of each video as closely as possible. Cross correlation is a mathematical technique used to find the amount of offset between different signals. In this case, Skelly Synchronize is using cross correlation to find the time difference between the audio tracks of the video files.

**Brightness Contrast Detection** synchronizes by looking for a quick flash near the beginning of each video. This flash can be from a camera flash, turning on a light, or even opening curtains to a bright window. Skelly Synchronize looks for the first time in each video that the change in brightness (contrast) between subsequent frames passes a certain threshold, and then aligns the brightness change of each video. The brightness contrast threshold used can be set as a parameter in the web UI, and higher threshold values will require a more abrupt and brighter flash in the video. Synchronization will be best if all cameras see the flash at the same time, so methods like turning on a light will yield better synchronization than methods like opening curtains.

### Video Requirements

For **audio synchronization**, all videos must have audio tracks. Synchronization will work better if there are short, distinct sounds audible from each camera, for example a loud clap.

For **brightness synchronization**, there must be a quick increase in brightness across all of the video files. This method requires a significant brightness change visible to all cameras, for example turning on a bright light or firing a flash visible to all cameras. The synchronization will be based off of the first brightness change in each video that crosses a threshold. You can set the brightness ratio threshold in the web UI before synchronizing. The threshold takes into account both the brightness contrast compared to the preceding frame, and the rate of change of brightness contrast. It may take multiple tries with different brightness ratio thresholds to get proper synchronization, although the default should work in most cases.

### Additional Files

Skelly synchronize will create a variety of additional files during synchronization, depending on what synchronization method is used and what preprocessing steps are required for your videos.

Two debug files will always be created. The first, `debug_plot.png`, shows a visualization of the videos pre and post synchronization to give visual confirmation of the synchronization process. The second, `synchronization_debug.toml`, gives information on both the raw and synchronized videos, and provides the lag dictionary, which shows the offsets in seconds between the start of each raw video and the first moment all videos recorded.

Videos that do not have the same framerate (and audio files that do not have the same sample rate) will be normalized to have matching framerates, which will create a "normalized_videos" folder inside of the raw videos folder that has normalized copies of the original videos. 

Audio synchronization will place the extracted audio files into the synchronized video folder. Brightness synching will place numpy files containing the brightness of the videos across time in both the raw and synchronized video folders.
