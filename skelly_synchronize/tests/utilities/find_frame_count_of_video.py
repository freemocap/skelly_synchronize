import cv2


def find_frame_count_of_video(video_pathstring: str):
    video_capture_object = cv2.VideoCapture(video_pathstring)
    frame_count = video_capture_object.get(cv2.CAP_PROP_FRAME_COUNT)
    video_capture_object.release()

    return int(frame_count)
