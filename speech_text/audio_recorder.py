import queue
import sounddevice as sd
import threading
from soundfile import SoundFile
from typing import Iterable, Callable
from datetime import datetime
import os


class AudioWriter:
    """Write audio data to sound file"""

    def __init__(self, output_path: str, sample_rate: int | None = None) -> None:
        # self._sample_rate = sample_rate or int(
        #     sd.query_devices(kind="input")["default_samplerate"]
        # )
        self._sample_rate = sample_rate

        if not output_path.endswith(".wav"):
            output_path += ".wav"

        self._soundfile = SoundFile(
            output_path, mode="x", samplerate=self._sample_rate, channels=1
        )

    def __enter__(self) -> SoundFile:
        return self._soundfile

    def __exit__(self, _type, _value, _traceback) -> None:
        self._soundfile.close()


class MicReader:
    """Get input from microphone"""

    def __init__(self, sample_rate: int, duration: int, mic_rec_callback: Callable | None = None) -> None:
        self._mic_rec_callback = mic_rec_callback
        self._mic_queue = queue.SimpleQueue()
        self._stop_event = threading.Event()
        self.start_time = datetime.now()
        self.sample_rate = sample_rate
        self.duration = duration + 1

    def mic_audio_gen(self) -> Iterable[bytes]:
        stream = sd.InputStream(
            channels=1,
            samplerate=self.sample_rate,
            callback=self._audio_callback,
            dtype="int16",
        )

        with stream:
            while True:
                chunk = self._mic_queue.get()
                if not chunk:
                    break
                yield chunk

    def close(self) -> None:
        self._stop_event.set()

    def _audio_callback(self, indata, _frames, _time, status) -> None:
        """This is called (from a separate thread) for each audio block."""
        if self._stop_event.is_set():
            self._mic_queue.put(None)
        if (datetime.now() - self.start_time).seconds >= self.duration:
            self.close()
        else:
            self._mic_queue.put(indata.tobytes())
            if self._mic_rec_callback:
                try:
                    self._mic_rec_callback(indata)
                except RuntimeError:
                    print("Warning: writing audio runtime error")


class MicRecorder:
    def __init__(self, sample_rate, output_dir):
        self.sample_rate = sample_rate
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._stop_flag = False

    def record(self, durations: int):
        print(f"Recording for {durations} seconds....")
        self._stop_flag = False
        rec_path = os.path.join(self.output_dir, f"{datetime.now().strftime('%y-%m-%d_%H-%M-%S')}.wav")

        with AudioWriter(rec_path, sample_rate=self.sample_rate) as audio_writer:
            mic_reader = MicReader(self.sample_rate, durations, mic_rec_callback=audio_writer.write)
            mic_input_gen = mic_reader.mic_audio_gen()
            for _ in mic_input_gen:
                if self._stop_flag is True:
                    break

            mic_reader.close()
        return rec_path

    def stop(self):
        self._stop_flag = True


if __name__ == "__main__":
    mic_recorder = MicRecorder(sample_rate=16000, output_dir="tmp/")
    print(mic_recorder.record(3))
