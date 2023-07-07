import librosa
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
import plotly.colors as colors
from pathlib import Path
from typing import List

from skelly_synchronize.system.paths_and_file_names import (
    DEBUG_PLOT_NAME,
    AUDIO_FILES_FOLDER_NAME,
    TRIMMED_AUDIO_FOLDER_NAME,
)


def create_debug_plots(synchronized_video_folder_path: Path):
    output_filepath = synchronized_video_folder_path / DEBUG_PLOT_NAME
    raw_audio_folder_path = synchronized_video_folder_path / AUDIO_FILES_FOLDER_NAME
    trimmed_audio_folder_path = raw_audio_folder_path / TRIMMED_AUDIO_FOLDER_NAME

    list_of_raw_audio_paths = get_audio_paths_from_folder(raw_audio_folder_path)
    list_of_trimmed_audio_paths = get_audio_paths_from_folder(trimmed_audio_folder_path)

    plot_waveforms(
        raw_audio_filepath_list=list_of_raw_audio_paths,
        trimmed_audio_filepath_list=list_of_trimmed_audio_paths,
        output_filepath=output_filepath,
    )


def get_audio_paths_from_folder(
    folder_path: Path, file_extension: str = ".wav"
) -> List[Path]:
    search_extension = "*" + file_extension.lower()
    return Path(folder_path).glob(search_extension)


def plot_waveforms(
    raw_audio_filepath_list: List[Path],
    trimmed_audio_filepath_list: List[Path],
    output_filepath: Path,
):
    # Create a subplot with 2 rows and 1 column
    fig = sp.make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=("Before Cross Correlation", "After Cross Correlation"),
    )

    color_list = colors.DEFAULT_PLOTLY_COLORS

    for idx, audio_filepath in enumerate(raw_audio_filepath_list):
        audio_signal, sr = librosa.load(path=audio_filepath, sr=None)
        time = np.linspace(0, len(audio_signal) / sr, num=len(audio_signal))
        fig.add_trace(
            go.Scatter(
                name=audio_filepath.stem,
                x=time,
                y=audio_signal,
                mode="lines",
                opacity=0.4,
                line=dict(color=color_list[idx % len(color_list)]),
            ),
            row=1,
            col=1,
        )

    for idx, audio_filepath in enumerate(trimmed_audio_filepath_list):
        audio_signal, sr = librosa.load(path=audio_filepath, sr=None)
        time = np.linspace(0, len(audio_signal) / sr, num=len(audio_signal))
        fig.add_trace(
            go.Scatter(
                name=audio_filepath.stem,
                x=time,
                y=audio_signal,
                mode="lines",
                opacity=0.4,
                line=dict(color=color_list[idx % len(color_list)]),
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        title="Audio Cross Correlation Debug",
        yaxis1=dict(title="Amplitude"),
        yaxis2=dict(title="Amplitude"),
        xaxis2=dict(title="Time (s)"),
    )

    fig.write_image(str(output_filepath))
