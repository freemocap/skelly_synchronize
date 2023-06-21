import logging
import cv2
from deffcode import Sourcer

logging.basicConfig(level=logging.INFO)


def check_if_video_has_reversed_metadata(video_pathstring: str):
    """
    Some vertical videos report as if they are landscape,
    and then have additional metadata indicating they need to be rotated.
    This is missed by ffmpeg, and the output videos are stretched into landscape.

    This function finds these videos by comparing the opencv and deffcode metadata.
    Opencv always shows the correct orientation, and deffcode show it swapped.
    This means videos where the libraries disagree require different handling.
    This function returns true if the video need to be transposed.
    """

    capture_object = cv2.VideoCapture(video_pathstring)
    if not capture_object.isOpened():
        raise Exception("Video could not be opened")
    opencv_width = int(capture_object.get(cv2.CAP_PROP_FRAME_WIDTH))
    opencv_height = int(capture_object.get(cv2.CAP_PROP_FRAME_HEIGHT))

    capture_object.release()

    sourcer = Sourcer(video_pathstring).probe_stream()

    metadata_dictionary = sourcer.retrieve_metadata()

    deffcode_width = metadata_dictionary["source_video_resolution"][0]
    deffcode_height = metadata_dictionary["source_video_resolution"][1]

    if (opencv_width != deffcode_width) & (opencv_height != deffcode_height):
        return True
    else:
        return False


if __name__ == "__main__":
    # video_pathstring = (
    #     "/Users/philipqueen/Downloads/portrait.mp4"  # this should be true
    # )
    # video_pathstring = '/Users/philipqueen/Documents/synch_test/RawVideos/Cam1.MP4' # this should be false
    video_pathstring = (
        "/Users/philipqueen/Downloads/HorizontalTest.mov"  # this should be false
    )

    print(check_if_video_has_reversed_metadata(video_pathstring=video_pathstring))
