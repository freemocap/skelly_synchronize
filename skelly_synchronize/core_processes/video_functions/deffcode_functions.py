import json
import logging
import cv2
from deffcode import FFdecoder

from skelly_synchronize.utils.check_if_video_has_reversed_metadata import (
    check_if_video_has_reversed_metadata,
)


def trim_single_video_deffcode(
    input_video_pathstring: str,
    frame_list: list,
    output_video_pathstring: str,
):
    vertical_video_bool = check_if_video_has_reversed_metadata(
        video_pathstring=input_video_pathstring
    )

    if vertical_video_bool:
        logging.info("Video has reversed metadata, changing FFmpeg transpose argument")
        ffparams = {"-ffprefixes": ["-noautorotate"], "-vf": "transpose=1"}
    else:
        ffparams = {}

    decoder = FFdecoder(
        str(input_video_pathstring),
        frame_format="bgr24",
        verbose=False,
        **ffparams,
    ).formulate()

    metadata_dictionary = json.loads(decoder.metadata)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    framerate = metadata_dictionary["output_framerate"]
    framesize = tuple(metadata_dictionary["output_frames_resolution"])

    video_writer_object = cv2.VideoWriter(
        output_video_pathstring, fourcc, framerate, framesize
    )

    current_frame = 0
    written_frames = 0

    for frame in decoder.generateFrame():
        if frame is None:
            break

        if current_frame in frame_list:
            video_writer_object.write(frame)
            written_frames += 1

        if written_frames == len(frame_list):
            break

        current_frame += 1

    decoder.terminate()
    video_writer_object.release()
