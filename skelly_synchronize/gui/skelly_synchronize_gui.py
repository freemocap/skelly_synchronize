from pathlib import Path
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QMainWindow,
    QLabel,
    QLineEdit,
    QHBoxLayout,
)

from skelly_synchronize.skelly_synchronize import (
    synchronize_videos_from_audio,
    synchronize_videos_from_brightness,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._folder_path = None

        self.setGeometry(100, 100, 600, 300)

        widget = QWidget()
        self._layout = QVBoxLayout()
        widget.setLayout(self._layout)
        self.setCentralWidget(widget)

        self.folder_open_button = QPushButton("Load folder of raw videos")
        self._layout.addWidget(self.folder_open_button)
        self.folder_open_button.clicked.connect(self._open_session_folder_dialog)

        self.folder_path_label = QLabel(
            f"Selected folder of raw videos: {self._folder_path}"
        )
        self.folder_path_label.setFixedHeight(15)
        self._layout.addWidget(self.folder_path_label)

        self.run_audio_synch_button = QPushButton(
            "Synchronize videos with Audio Cross Correlation"
        )
        self.run_audio_synch_button.setEnabled(False)
        self._layout.addWidget(self.run_audio_synch_button)
        self.run_audio_synch_button.clicked.connect(
            lambda: synchronize_videos_from_audio(
                raw_video_folder_path=self._folder_path
            )
        )

        self.run_brightness_synch_button = QPushButton(
            "Synchronize videos with First Brightness Change"
        )
        self.run_brightness_synch_button.setEnabled(False)
        self._layout.addWidget(self.run_brightness_synch_button)

        hbox = QHBoxLayout()
        brightness_threshold_default = 1000
        hbox.addWidget(QLabel("Brightness ratio threshold: "))
        self.brightness_threshold_lineedit = QLineEdit()
        self.brightness_threshold_lineedit.setText(str(brightness_threshold_default))
        validator = QDoubleValidator()
        validator.setBottom(1)
        self.brightness_threshold_lineedit.setValidator(validator)
        hbox.addWidget(self.brightness_threshold_lineedit)
        self._layout.addLayout(hbox)

        self.run_brightness_synch_button.clicked.connect(
            lambda: synchronize_videos_from_brightness(
                raw_video_folder_path=self._folder_path,
                brightness_ratio_threshold=float(
                    self.brightness_threshold_lineedit.text()
                ),
            )
        )

    def _open_session_folder_dialog(self):
        folder_input = QFileDialog.getExistingDirectory(None, "Choose a folder")
        self._folder_path = Path(folder_input)
        self.folder_path_label.setText(
            f"Selected folder of raw videos: {self._folder_path}"
        )
        self.run_audio_synch_button.setEnabled(True)
        self.run_brightness_synch_button.setEnabled(True)


def main():
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
