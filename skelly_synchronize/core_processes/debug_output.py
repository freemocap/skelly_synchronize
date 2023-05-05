import toml
from pathlib import Path


def save_dictionaries_to_toml(input_dictionaries: dict, output_file_path: Path):
    """Saves informative dictionaries to a TOML file for debugging"""
    with open(output_file_path, "w") as toml_file:
        for idx, (name, dictionary) in enumerate(input_dictionaries.items()):
            toml_file.write(f"[{name}]\n")
            toml_file.write(toml.dumps(dictionary))
            if idx < len(input_dictionaries) - 1:
                toml_file.write("\n")


def remove_audio_files_from_audio_signal_dict(audio_signal_dictionary: dict) -> dict:
    """Remove audio files from audio signal dict to reduce unnessary storage"""
    for audio_info_dictionary in audio_signal_dictionary.values():
        audio_info_dictionary.pop("audio file")

    return audio_signal_dictionary
