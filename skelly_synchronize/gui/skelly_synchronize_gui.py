from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QMainWindow,
)

from gui.widgets.run_button_widget import RunButtonWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setGeometry(100, 100, 600, 600)

        widget = QWidget()
        self._layout = QVBoxLayout()
        widget.setLayout(self._layout)
        self.setCentralWidget(widget)

        self.folder_open_button = QPushButton("Load a folder")
        self._layout.addWidget(self.folder_open_button)
        self.folder_open_button.clicked.connect(self._open_session_folder_dialog)

        self.run_button = RunButtonWidget()
        self._layout.addWidget(self.run_button)

    def _open_session_folder_dialog(self):
        self._folder_path = QFileDialog.getExistingDirectory(None, "Choose a folder")
        print(self._folder_path)


def main():
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
