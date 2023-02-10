import os
import sys
import librosa
import time
import logging
import moviepy.editor as mp
import numpy as np
from glob import glob
from scipy import signal
from pathlib import Path

logging.basicConfig(level = logging.DEBUG)

class VideoSynchTrimming:
    '''Class of functions for time synchronizing and trimming video files based on cross correlation of their audio.'''
    
    def __init__(self, sessionID: str, fmc_data_path: Path) -> None:
        '''Initialize VideoSynchTrimmingClass'''
        self.base_path = fmc_data_path / sessionID

        self.raw_video_folder_name = "RawVideos"
        self.raw_video_path = self.base_path / self.raw_video_folder_name
        self.synced_video_folder_name = "SyncedVideos"
        self.synced_video_path = self.base_path / self.synced_video_folder_name
        self.audio_folder_name = "AudioFiles"
        self.audio_folder_path = self.base_path / self.audio_folder_name

        # create synced video and audio file folders
        os.makedirs(self.synced_video_path, exist_ok=True)
        os.makedirs(self.audio_folder_path, exist_ok=True)


    def get_clip_list(self, file_type: str) -> list:
        '''Return a list of all video files in the base_path folder that match the given file type.'''

        # create general search from file type to use in glob search, including cases for upper and lowercase file types
        file_extension_upper = '*' + file_type.upper()
        file_extension_lower = '*' + file_type.lower()
    
        # make list of all files with file type
        clip_list = glob(file_extension_upper) + glob(file_extension_lower) #if two capitalization standards are used, the videos may not be in original order
        
        # because glob behaves differently on windows vs. mac/linux, we collect all files both upper and lowercase, and remove redundant files that appear on windows
        unique_clip_list = self.get_unique_list(clip_list)
        
        return unique_clip_list

    def get_files(self, clip_list: list) -> list:
        '''Get video files from clip_list, extract the audio, and put the video and audio files in a list.
        Return a list of lists containing the video file name and file, and audio name and file.
        Also return a list containing the audio sample rate from each file.'''
    
        # create empty list for storing audio and video files, will contain sublists formatted like [video_file_name,video_file,audio_file_name,audio_file] 
        file_list = []
        # create empty list to hold audio sample rate, so we can verify samplerate is the same across all audio files
        sample_rate_list = []

        # iterate through clip_list, open video files and audio files, and store in file_list
        for clip in clip_list:
            # take vid_name and change extension to create audio file name
            vid_name = clip
            audio_name = clip.split(".")[0] + '.wav'
            # open video files
            video_file = mp.VideoFileClip(str(self.raw_video_path / vid_name), audio=True)
            logging.info(f"video size is {video_file.size}")
            # waiting on moviepy to fix issue related to portrait mode videos having height and width swapped
            video_file = video_file.resize((1080,1920)) #hacky workaround for iPhone portrait mode videos
            logging.info(f"resized video is {video_file.size}")

            # get length of video clip
            vid_length = video_file.duration

            # create .wav file of clip audio
            video_file.audio.write_audiofile(str(self.audio_folder_path / audio_name))

            # extract raw audio from Wav file
            audio_signal, audio_rate = librosa.load(self.audio_folder_path / audio_name, sr = None)
            sample_rate_list.append(audio_rate)

            # save video and audio file names and files in list
            file_list.append([vid_name, video_file, audio_name, audio_signal])

            logging.info(f"video length: {vid_length} seconds, audio sample rate {audio_rate} Hz")

        return file_list, sample_rate_list

    def get_unique_list(self, list: list) -> list:
        '''Return a list of the unique elements from input list'''
        unique_list = []
        [unique_list.append(clip) for clip in list if clip not in unique_list]

        return unique_list
        

    def get_fps_list(self, file_list: list) -> list:
        '''Retrieve frames per second of each video clip in file_list'''
        return [file[1].fps for file in file_list]

    def check_rates(self, rate_list: list):
        '''Check if audio sample rates or video frame rates are equal, throw an exception if not (or if no rates are given).'''
        if len(rate_list) == 0:
            raise Exception("no rates given")
        
        if rate_list.count(rate_list[0]) == len(rate_list):
            logging.debug(f"all rates are equal to {rate_list[0]}")
            return rate_list[0]
        else:
            raise Exception(f"rates are not equal, rates are {rate_list}")

    def normalize_audio(self, audio_file):
        '''Perform z-score normalization on an audio file and return the normalized audio file - this is best practice for correlating.'''
        return ((audio_file - np.mean(audio_file))/np.std(audio_file - np.mean(audio_file)))

    def cross_correlate(self, audio1, audio2):
        '''Take two audio files, sync them using cross correlation, and trim them to the same length.
        Inputs are two WAV files to be synced. Return the lag expressed in terms of the audio sample rate of the clips.
        '''

        # compute cross correlation with scipy correlate function, which gives the correlation of every different lag value
        # mode='full' makes sure every lag value possible between the two signals is used, and method='fft' uses the fast fourier transform to speed the process up 
        corr = signal.correlate(audio1, audio2, mode='full', method='fft')
        # lags gives the amount of time shift used at each index, corresponding to the index of the correlate output list
        lags = signal.correlation_lags(audio1.size, audio2.size, mode="full")
        # lag is the time shift used at the point of maximum correlation - this is the key value used for shifting our audio/video
        lag = lags[np.argmax(corr)]

        return lag

    def find_lags(self, file_list: list, sample_rate: int) -> list:
        '''Take a file list containing video and audio files, as well as the sample rate of the audio, cross correlate the audio files, and output a lag list.
        The lag list is normalized so that the lag of the latest video to start in time is 0, and all other lags are positive.
        '''
        lag_list = [self.cross_correlate(file_list[0][3],file[3])/sample_rate for file in file_list] # cross correlates all audio to the first audio file in the list
        #also divides by the audio sample rate in order to get the lag in seconds
        
        #now that we have our lag array, we subtract every value in the array from the max value
        #this creates a normalized lag array where the latest video has lag of 0
        #the max value lag represents the latest video - thanks Oliver for figuring this out
        norm_lag_list = [(max(lag_list) - value) for value in lag_list]
        
        logging.debug(f"original lag list: {lag_list} normalized lag list: {norm_lag_list}")
        
        return norm_lag_list
    
    def find_minimum_video_duration(self, file_list: list, lag_list: list) -> float:
        '''Take a list of video files and a list of lags, and find what the shortest video is starting from each videos lag offset'''
        
        min_duration = min([file_list[index][1].duration - lag_list[index] for index in range(len(file_list))])
        
        return min_duration


    
    def trim_videos(self, file_list: list, lag_list: list) -> list:
        '''Take a list of video files and a list of lags, and make all videos start and end at the same time.
        Must be in folder of file list'''

        min_duration = self.find_minimum_video_duration(file_list, lag_list)

        trimmed_video_filenames = [] # can be used for plotting

        for index in range(len(file_list)):
            logging.debug(f"trimming video file {file_list[index][1]}")
            trimmed_video = file_list[index][1].subclip(lag_list[index],lag_list[index] + min_duration)
            if file_list[index][0].split("_")[0] == "raw":
                video_name = "synced_" + file_list[index][0][4:]
            else:
                video_name = "synced_" + file_list[index][0]
            trimmed_video_filenames.append(video_name) #add new name to list to reference for plotting
            logging.debug(f"video size is {trimmed_video.size}")
            trimmed_video.write_videofile(video_name)
            logging.info(f"Video Saved - Cam name: {video_name}, Video Duration: {trimmed_video.duration}")

        return trimmed_video_filenames

    def front_trim_videos(self, file_list: list, lag_list: list) -> list:
        '''Take a list of video files and a list of lags, and shortens the beginnings of the videos by the lags to ensure they all start at the same time
        Must be in folder of file list'''
        front_trimmed_videos = []

        # for each video in the list, create a new video trimmed from the begining by the lag value for that video, and add it to the empty list
        for i in range(len(file_list)):
            logging.debug(f"trimming video file {file_list[i][1]}")
            front_trimmed_video = file_list[i][1].subclip(lag_list[i],file_list[i][1].duration)
            #front_trimmed_video = file_list[i][1].subclip(lag_list[i]) # this is a cleaner way of writing this, but needs testing
            front_trimmed_videos.append([file_list[i][0], front_trimmed_video])

        return front_trimmed_videos

    def back_trim_videos(self, video_list: list) -> list:
        '''Take a list of video files and trims the ends of the videos to ensure they're all the same length'''
        min_duration = min([video[1].duration for video in video_list])
        logging.debug(f"shortest video is {min_duration}")

        # create list to store names of final videos
        video_names = []
        # trim all videos to length of shortest video, and give it a new name
        for video in video_list:
            fully_trimmed_video = video[1].subclip(0,min_duration)
            if video[0].split("_")[0] == "raw":
                video_name = "synced_" + video[0][4:]
            else:
                video_name = "synced_" + video[0]
            video_names.append(video_name) #add new name to list to reference for plotting
            logging.debug(f"video size is {fully_trimmed_video.size}")
            fully_trimmed_video.write_videofile(video_name)
            logging.info(f"Video Saved - Cam name: {video_name}, Video Duration: {fully_trimmed_video.duration}")


def sync_videos(sessionID: str, fmc_data_path: Path, file_type: str) -> None:
    '''Run the functions from the VideoSynchTrimming class to sync all videos with the given file type in the base path folder.
    file_type can be given in either case, with or without a leading period
    '''
    # instantiate class
    synch_and_trim = VideoSynchTrimming(sessionID, fmc_data_path)
    # the rest of this could theoretically be put in the init function, don't know which is best practice...

    os.chdir(synch_and_trim.raw_video_path)
    # create list of video clips in raw video folder
    clip_list = synch_and_trim.get_clip_list(file_type)
    os.chdir(synch_and_trim.base_path)

    # get the files and sample rate of videos in raw video folder, and store in list
    files, audio_sample_rates = synch_and_trim.get_files(clip_list)

    # find the frames per second of each video
    fps_list = synch_and_trim.get_fps_list(files)
    
    # frame rates and audio sample rates must be the same duration for the trimming process to work correctly
    synch_and_trim.check_rates(fps_list)
    synch_and_trim.check_rates(audio_sample_rates)
    
    # find the lags between starting times
    lag_list = synch_and_trim.find_lags(files, audio_sample_rates[0])
    
    # use lags to trim the videos
    os.chdir(synch_and_trim.synced_video_path)
    #front_trimmed_videos = synch_and_trim.front_trim_videos(files, lag_list)
    #fully_trimmed_videos = synch_and_trim.back_trim_videos(front_trimmed_videos)
    trimmed_videos = synch_and_trim.trim_videos(files, lag_list)
    os.chdir(synch_and_trim.base_path)

def main(sessionID: str, fmc_data_path: Path, file_type: str):
    # start timer to measure performance
    start_timer = time.time()

    sync_videos(sessionID, fmc_data_path, file_type)

    # end performance timer
    end_timer = time.time()
    
    #calculate and display elapsed processing time
    elapsed_time = end_timer - start_timer
    logging.info(f"elapsed processing time in seconds: {elapsed_time}")


if __name__ == "__main__":
    sessionID = "iPhoneTesting"
    fmc_data_path = Path("/Users/philipqueen/Documents/Humon Research Lab/FreeMocap_Data")
    file_type = "MP4"
    main(sessionID, fmc_data_path, file_type)