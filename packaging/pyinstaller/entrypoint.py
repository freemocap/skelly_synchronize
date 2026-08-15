"""PyInstaller entry script for the skelly-sync-api sidecar.

A real script file (not a package import string) is needed as the
Analysis() entry point; it just calls the same run() the skelly-sync-api
console script calls.
"""

from skelly_synchronize.api.main import run

if __name__ == "__main__":
    run()
