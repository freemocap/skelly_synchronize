# __main__.py
import sys
from pathlib import Path

base_package_path = Path(__file__).parent.parent
print(f"adding base_package_path: {base_package_path} : to sys.path")
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path

#from skelly_synchronize.skelly_synchronize import main
from gui.skelly_synchronize_gui import main

if __name__ == "__main__":
    main()
    #sessionID = "your_session_id"
    #freemocap_data_path = Path("path_to_your_freemocap_data_folder")
    #file_type = "MP4"
    #main(sessionID, freemocap_data_path, file_type)
