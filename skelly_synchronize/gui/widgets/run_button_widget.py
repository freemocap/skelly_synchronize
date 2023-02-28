from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class RunButtonWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._layout = QVBoxLayout()
        self.setLayout = self._layout

        self.run_button_widget = QPushButton("Run", self)

        # self.run_button_widget.clicked.connect(self.run_script)

    def run_script(self):
        print("Running a print statement!")
