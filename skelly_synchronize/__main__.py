# __main__.py
import sys
from pathlib import Path
import argparse

base_package_path = Path(__file__).parent.parent
print(f"adding base_package_path: {base_package_path} : to sys.path")
sys.path.insert(0, str(base_package_path))  # add parent directory to sys.path

def parse_args():
    parser = argparse.ArgumentParser(description="Skelly Synchronize")
    return parser.parse_args()

def run():
    parse_args()

    from gui.skelly_synchronize_gui import main
    main()


if __name__ == "__main__":
    run()
