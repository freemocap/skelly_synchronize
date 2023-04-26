import cv2


def check_if_video_is_vertical(video_pathstring: str):
    """Check if the video is vertical or not. Returns True if the video is vertical, False otherwise."""

    capture_object = cv2.VideoCapture(video_pathstring)
    if not capture_object.isOpened():
        raise Exception("Video could not be opened")
    width = int(capture_object.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture_object.get(cv2.CAP_PROP_FRAME_HEIGHT))

    capture_object.release()
    if width < height:
        return True
    else:
        return False
