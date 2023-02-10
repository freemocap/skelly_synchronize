import moviepy.editor as mp

mp4_pathstring = "/Users/philipqueen/Documents/Humon Research Lab/FreeMocap_Data/iPhoneTesting/RawVideos/Cam0.mp4"
mov_pathstring = "/Users/philipqueen/Downloads/Cam0.MOV"

mp4_video = mp.VideoFileClip(mp4_pathstring)
print(f"mp4 video is size: {mp4_video.size}")

mov_video = mp.VideoFileClip(mov_pathstring)
print(f"mov video is size: {mov_video.size}")

