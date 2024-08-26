import json
import logging
import cv2
from deffcode import FFdecoder, Sourcer

tranposition_dictionary = {
    90.0: "transpose=cclock",
    -270.0: "transpose=cclock",
    -90.0: "transpose=clock",
    270.0: "transpose=clock",
    180.0: "transpose=cclock,transpose=cclock",
}

logger = logging.getLogger(__name__)


def trim_single_video_deffcode(
    input_video_pathstring: str,
    frame_list: list,
    output_video_pathstring: str,
):
    sourcer = Sourcer(input_video_pathstring).probe_stream()
    metadata_dictionary = sourcer.retrieve_metadata()

    if metadata_dictionary["source_video_orientation"] != 0:
        logging.info("Video has reversed metadata, changing FFmpeg transpose argument")
        ffparams = {
            "-ffprefixes": ["-noautorotate"],
            "-vf": tranposition_dictionary[
                metadata_dictionary["source_video_orientation"]
            ],
        }
    else:
        ffparams = {}

    decoder = FFdecoder(
        str(input_video_pathstring),
        frame_format="bgr24",
        verbose=False,
        **ffparams,
    ).formulate()

    metadata_dictionary = json.loads(decoder.metadata)

    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
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
