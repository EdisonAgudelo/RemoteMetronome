
from PyQt6 import QtCore, QtGui, QtWidgets
from view._main import Ui_Metronome
import sys


class MainUI(Ui_Metronome):

    def __init__(self) -> None:
        super().__init__()


    def browse_file(self, input_to_modify:QtWidgets.QLineEdit, filter="", caption="Select a file"):
        file_name = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.win,
            caption=caption,
            filter=filter,
        )

        input_to_modify.setText(file_name[0])


    def __load_events(self):
        
        self.h_sound_button.clicked.connect(lambda: self.browse_file(self.h_sound_input, "WAV file (*.wav)", "Select H sound"))
        self.l_sound_button.clicked.connect(lambda: self.browse_file(self.l_sound_input, "WAV file (*.wav)", "Select L sound"))
        
        self.interface_combo_box.currentIndexChanged.connect(self._onInterfaceSelectionChange)
        self.channel_combo_box.currentIndexChanged.connect(self._onChannelSelectionChange)
        self.sample_combo_box.currentIndexChanged.connect(self._onSampleRateSelectionChange)
        self.h_sound_input.textChanged.connect(self._onSoundChange)
        self.l_sound_input.textChanged.connect(self._onSoundChange)
        self.index_combo_box.currentIndexChanged.connect(self._onIndexChange)

        self.control_button.clicked.connect(self._onControlEvent)

        interfaces_name, interfaces_channels = self.get_interfaces()
        index = 0

        self.index_combo_box.clear()
        self.index_combo_box.addItems(self.get_index_available()) 

        self.interface_combo_box.clear()
        for name in interfaces_name:
            self.interface_combo_box.addItem(name, interfaces_channels[index])
            index += 1

        self.set_app_icon(self.get_icon_path())
        self.win.setWindowTitle(f"Metronome - {self.get_app_version()}")

    def get_current_audio_samples(self) -> list[str,str]:
        return [self.h_sound_input.text(), self.l_sound_input.text()]

    def get_current_output_config(self) -> tuple[str, str]:
        return (self.interface_combo_box.currentText(), self.channel_combo_box.currentText(), int(self.sample_combo_box.currentText().split(' ')[0]))

    def get_current_index(self):
        return self.index_combo_box.currentText()

    def set_app_icon(self, path):
        self.win.setWindowIcon(QtGui.QIcon(path))

    def _onInterfaceSelectionChange(self):

        current_index = self.interface_combo_box.currentIndex()
        available_channels = self.interface_combo_box.itemData(current_index)

        self.channel_combo_box.clear()
        self.channel_combo_box.addItems([str(i + 1) for i in range(available_channels)])

    def get_index_available(self) -> list[str]:
        return []

    def get_interfaces(self) -> tuple[list[str], list[int]]:
        #should be implemented on subclass
        return ([], [])

    def get_app_version(self) -> str:
        """
        place holder for subclass
        """

    def get_icon_path(self) -> str:
        """
        place holder for subclass
        """

    def _onIndexChange(self):
        """
        place holder for subclass
        """

    def _onChannelSelectionChange(self):
        """
        place holder for subclass
        """

    def _onSampleRateSelectionChange(self):
        """
        place holder for subclass
        """

    def _onControlEvent(self):
        """
        Place holder for subclass
        """

    def _onSoundChange():
        """
        place holder for subclass
        """

    def start(self):  
        self.app = QtWidgets.QApplication(sys.argv)
        self.win = QtWidgets.QMainWindow()
        self.setupUi(self.win)
        self.win.show()

        self.__load_events()

        self.app.exec()