
import PyWave  
import threading
import flask_sock
import sounddevice as sd
import numpy as np


class AudioBackend():

    def __init__(self) -> None:
        ...
    def open(self, width,  channels , rate , output = False, input = False, stream_callback = None, frames_per_buffer = 1024, output_device_id = None, input_device_id = None, float = False):
        def widthtodtype(size):
            return f'{"float" if float else "int"}{8*size}'

        def callback_wrapper(out_buffer, *arg, **kargs):
            try:
                out_buffer[:] = stream_callback()
            except Exception as e:
                print(f"Error on buffer creation: {str(e)}")
                
        self._stream = sd.RawOutputStream(samplerate=rate, blocksize=frames_per_buffer, channels=channels, callback=callback_wrapper, device=output_device_id, dtype=widthtodtype(width))
        self._stream.start()

    def available_interfaces(self):
        devices = sd.query_devices()
        hostapi_names = [hostapi['name'] for hostapi in sd.query_hostapis()]
        interfaces = [
            {
                "id": device["index"], 
                "name":  hostapi_names[device['hostapi']] + " - " + device['name'], 
                "channels": int(device["max_output_channels"]), 
                "host_api": device['hostapi']
            }
            for device in devices if int(device["max_output_channels"]) > 0
        ]

        return interfaces

    def close(self):
        try:
            self._stream.close()
        except Exception as e:
            print(f"Can't close stream {e}")


class IntervalPlayer(AudioBackend):

    _chunk = 1024  

    def __init__(self, sample_files:list[str], device_id = None, channel_offset = None, sample_rate = 48000) -> None:

        super().__init__()

        if channel_offset == None:
            channel_offset = 1
        
        channel_offset -= 1

        self._current_sample = 0
        self._play_interval = 0
        self._mute = True
        self._close_stream = False

        f = PyWave.open(sample_files[0])  
        self._rate = f.frequency
        channels = f.channels
        width = f.bytes_per_sample
        is_float = f.format == PyWave.WAVE_FORMAT_IEEE_FLOAT

        self._frames_in_audio = [f.samples]
        self._audio_data = [f.read()]

        f.close()


        for file in sample_files[1:]:
            f = PyWave.open(file)
            if self._rate != f.frequency or channels != f.channels or width != f.bytes_per_sample:
                raise Exception("Incompatible samples requested")

            frames_in_audio = f.samples
            self._frames_in_audio.append(frames_in_audio)
            self._audio_data.append(f.read())

            f.close()

        #create an empty buffer just to emulate silence
        self._frame_size = (channels + channel_offset)* width
        self._frame_point = 0
        self._dumy_frame = b'\x00' * (self._chunk * self._frame_size)
        


        def decode(buffer, channels, size):
            """
            Samples are interleaved, so for a stereo stream with left channel 
            of [L0, L1, L2, ...] and right channel of [R0, R1, R2, ...], the output 
            is ordered as [L0, R0, L1, R1, ...]
            """

            chunk_size = len(buffer) // channels

            result = [b''] * channels
            frame_size = channels * size

            for sample in range(chunk_size):
                for ch in range(channels):
                    result[ch] += buffer[sample*frame_size + ch*size: sample*frame_size + size*(ch + 1)]

            return result


        def encode(buffer, size):
            
            chunk_size = len(buffer[0])

            result = b''

            for i in range(chunk_size):
                for ch in buffer:
                    result += ch[i*size:(i+1)*size]

            return result

        def add_extra_channels_ahead(buffer, extra_channels):

            extra_tamplate = b'\x00' * len(buffer[0])
            extra_channels_buffer:list = [extra_tamplate] * extra_channels
            extra_channels_buffer.extend(buffer)
            return extra_channels_buffer


        def resample(buffer, width, is_float, org_rate, new_rate):
            
            resample_factor = new_rate / org_rate

            if width != 3:
                array = buffer
            else:
                array = []
                for sample in buffer:
                    data = b""
                    for i in range(len(sample) // width):
                        data +=  int.from_bytes(sample[i*width:(i+1)*width], "little", signed=True).to_bytes(4, "little", signed=True)
                    array.append(data)

            index = 0
            for channel_sample in array:
                if width == 2:
                    dtype = np.dtype(np.int16).newbyteorder('<')
                elif is_float:
                    dtype = np.dtype(np.float32).newbyteorder('<')
                else:
                    dtype = np.dtype(np.int32).newbyteorder('<')
    
                channel_sample = np.frombuffer(channel_sample, dtype=dtype)
                #array = signal.resample_poly(array, int( len(array) * resample_factor), 1)
                n =  int( len(channel_sample) * resample_factor)
                channel_sample = np.interp(
                    np.linspace(0.0, 1.0, n, endpoint=False),  # where to interpret
                    np.linspace(0.0, 1.0, len(channel_sample), endpoint=False),  # known positions
                    channel_sample,  # known data points
                )
                channel_sample = channel_sample.astype(dtype).tobytes()
                if width == 3:
                    buffer[index] = b""
                    for byte_count in range(len(channel_sample)):
                        if (byte_count % 4) != 3:
                            buffer[index] += channel_sample[byte_count:byte_count+1]
                else:
                    buffer[index] = channel_sample
                index += 1

            return buffer


        if channel_offset or self._rate != sample_rate:
            #make a channel padding
            new_data = []
            sample_index = 0
            for data in self._audio_data:

                buffer = decode(data, channels, width)
                buffer = resample(buffer, width, is_float,self._rate, sample_rate)
                self._frames_in_audio[sample_index] = len(buffer[0]) // width
                buffer = add_extra_channels_ahead(buffer, channel_offset)
                new_data.append(encode(buffer, width))
                sample_index += 1
            self._audio_data = new_data
        #open stream  
        
        self.open(  width=width,  
                    channels = channels + channel_offset, 
                    rate = int(sample_rate),  
                    output = True,
                    stream_callback = self.__play_callback,
                    frames_per_buffer = self._chunk,
                    output_device_id=device_id,
                    float=is_float)

        
    def _get_next_sample_id(self) -> int:
        #should be reimplemented in a subclass
        return 0

    def __play_callback(self):

        if self._close_stream:
            return b""

        if self._mute:
            return self._dumy_frame


        def create_buffer(size):
            #ideally
            frames_to_end = self._play_interval - self._frame_point
            if frames_to_end > size:
                frames_to_end = size

            frames_from_audio = frames_to_end
            frames_from_dummy = 0
            
            #acording to pointer
            frames_in_audio_left = (self._frames_in_audio[self._current_sample] - self._frame_point) if self._frame_point < self._frames_in_audio[self._current_sample] else 0
            if frames_in_audio_left < frames_from_audio:
                frames_from_audio = frames_in_audio_left
                frames_from_dummy = frames_to_end - frames_from_audio


            buffer = self._audio_data[self._current_sample][(self._frame_point) * self._frame_size : (self._frame_point + frames_from_audio)  * self._frame_size] + self._dumy_frame[0:frames_from_dummy * self._frame_size]
            
            self._frame_point += frames_to_end
            if self._frame_point >= self._play_interval:
                self._frame_point = 0
                self._current_sample = self._get_next_sample_id()

            if frames_to_end < size:
                return buffer + create_buffer(size - frames_to_end)

            return buffer
        
        return create_buffer(self._chunk)

    def _set_current_sample(self, id):
        self._current_sample = id

    def set_time_interval(self, interval:float):
        #translate sec to sample rate terms
        self._play_interval = int(interval * self._rate)

    @property
    def mute(self):
        return self._mute

    @mute.setter
    def mute(self, mute:bool):
        self._mute = mute
        if mute:
            self._frame_point = 0

    def close(self):
        super().close()
        #stop stream 
        self._close_stream = True 

class Metronome(IntervalPlayer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.task = None
        self.alive = False
        self.time_delay = 1
        self.__beat_count = 0
        self._bar_size = 4
        self.__bar_count = 0

        self._bar_event = threading.Event()
        self._beat_event = threading.Event()

    def _get_next_sample_id(self) -> int:
        self.beat_count += 1

        if self.beat_count >= self._bar_size:
            self.beat_count = 0
            self.bar_count += 1

        return 1 if self.beat_count >= 1 else 0

    def set_bar_size(self, bar_size):
        self._bar_size = bar_size
        self.bar_count = 1
        self.beat_count = 0

    @property
    def bar_count(self):
        return self.__bar_count

    @property
    def beat_count(self):
        return self.__beat_count

    @beat_count.setter
    def beat_count(self, value):
        self.__beat_count = value
        self._beat_event.set()

    @bar_count.setter
    def bar_count(self, value):
        self.__bar_count = value
        self._bar_event.set()

    def start(self, tempo:int):
        if tempo:
            self.tempo = tempo
            self.time_delay = 60/self.tempo

            self.set_time_interval(self.time_delay)
            
            if self.mute:
                self._set_current_sample(0)

            self.mute = False
        
    def bar_reporter(self, ws: flask_sock.Server):
        while(ws.connected and not self._close_stream):
            ws.send(self.bar_count)
            self._bar_event.wait()
            self._bar_event.clear()

        if (ws.connected):
            ws.close(1, "stream closed")

    def beat_reporter(self, ws: flask_sock.Server):
        while(ws.connected and not self._close_stream):
            if self.mute:
                beat = 0
            else:
                beat = self.beat_count + 1 if self.beat_count else 1
            ws.send(beat)

            self._beat_event.wait()
            self._beat_event.clear()

        if (ws.connected):
            ws.close(1, "stream closed")
    
    def stop(self):
        self.mute = True
        self.bar_count = 0
        self.beat_count = 0

    def close(self):
        super().close()

        self._bar_event.set()
        self._beat_event.set()