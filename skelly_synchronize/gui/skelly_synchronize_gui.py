from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QMainWindow,
    QLabel,
)

from gui.widgets.run_button_widget import RunButtonWidget
from skelly_synchronize.skelly_synchronize import synchronize_videos_from_audio


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

        self.run_button = RunButtonWidget()
        self.run_button.run_button_widget.setEnabled(False)
        self._layout.addWidget(self.run_button)
        self.run_button.run_button_widget.clicked.connect(
            lambda: synchronize_videos_from_audio(
                raw_video_folder_path=self._folder_path
            )
        )

    def _open_session_folder_dialog(self):
        folder_input = QFileDialog.getExistingDirectory(None, "Choose a folder")
        self._folder_path = Path(folder_input)
        self.folder_path_label.setText(
            f"Selected folder of raw videos: {self._folder_path}"
        )
        self.run_button.run_button_widget.setEnabled(True)


def main():
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
