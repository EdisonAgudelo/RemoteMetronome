
from back.metro import Metronome
from back.server import app as server
from back.server import set_metro, set_index, set_data_folders
from view.main import MainUI
import webbrowser
import threading
import os


INDEX_FOLDER = "back/templates"
DEFAULT_H = "Stick H.wav"
DEFAULT_L = "Stick L.wav"
DEFAULT_SOUNDS = [DEFAULT_H, DEFAULT_L]


class Main(MainUI):
    def __init__(self) -> None:
        super().__init__()

    def get_app_version(self):
        return "v1.0.0"

    def get_icon_path(self):
        return "metronome.png"

    def get_index_available(self) -> list[str]:
        return [f.name for f in os.scandir("back\\templates") if f.is_file()] 

    def get_interfaces(self) -> tuple[list[str], list[int]]:
        self.interfaces = self.metro.available_interfaces()

        names = []
        channels = []
        for interface in self.interfaces:
            names.append(interface["name"])
            channels.append(interface["channels"])

        return names, channels

    def reloadMetro(self):
        interface_name, channel, sample_rate = self.get_current_output_config()
        try:
            channel = int(channel)
        except:
            return

        device_id = None
        for interface in self.interfaces:
            if interface["name"] == interface_name:
                device_id = interface["id"]

        if device_id == None:
            channel = None
            print("No output device found!")
            self.show_error("Can't found requested output device id")
            return


        metro_running = not self.metro.mute
        if metro_running:
            current_bar_size = self.metro._bar_size
            current_tempo = self.metro.tempo
        
        self.metro.stop()
        self.metro.close()

        try:
            self.metro = Metronome(self.get_current_audio_samples(), device_id=device_id, channel_offset=channel, sample_rate = sample_rate)
        except FileNotFoundError:
            try:
                self.metro = Metronome(DEFAULT_SOUNDS, device_id=device_id, channel_offset=channel)
            except:
                pass
        except Exception as e:
            print(e)
            self.show_error(f"Can't set metronome configuration\n{str(e)}")
            try:
                self.metro = Metronome(DEFAULT_SOUNDS, device_id=device_id, channel_offset=channel)
            except:
                pass

        if metro_running:
            self.metro.set_bar_size(current_bar_size)
            self.metro.start(current_tempo)

        set_metro(self.metro)

    def _onSoundChange(self):
        self.reloadMetro()

    def _onChannelSelectionChange(self):
        self.reloadMetro()    
    
    def _onSampleRateSelectionChange(self):
        self.reloadMetro()

    def _onIndexChange(self):
        new_index = self.get_current_index()
        set_index(new_index)
        

    def _onControlEvent(self):
        webbrowser.open('http://localhost:2000')

    def start(self):
    
        self.metro = Metronome(DEFAULT_SOUNDS)
        #run server
        threading.Thread(target=server.run, kwargs={"debug":False, "port":2000, "host":"0.0.0.0"}, daemon =True).start()
        super().start()



if __name__ == '__main__':
    
    set_data_folders(os.getcwd())
    app = Main()
    app.start()

   