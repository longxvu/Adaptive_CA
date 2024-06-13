import queue
import pyaudio
import wave


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, channels: int = 1, rate: int = 16000, chunk_duration: float = 0.1, output_file=None) -> None:
        """The audio -- and generator -- is guaranteed to be on the main thread."""
        self._channels = channels
        self._rate = rate
        # chunk_duration default is 100ms (0.1s) -> 16000Hz -> 1600 frames per chunk
        self._chunk = int(self._rate * chunk_duration)
        self._format = pyaudio.paInt16

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True
        self.all_data = []
        self.output_file = output_file

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=self._format,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=self._channels,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Closes the stream, regardless of whether the connection was lost or not."""
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()
        if self.output_file:
            with wave.open(self.output_file, "wb") as wav_out:
                wav_out.setnchannels(self._channels)
                wav_out.setsampwidth(self._audio_interface.get_sample_size(self._format))
                wav_out.setframerate(self._rate)
                wav_out.writeframes(b"".join(self.all_data))

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer.
            Args:
                in_data: The audio data as a bytes object
                frame_count: The number of frames captured
                time_info: The time information
                status_flags: The status flags
            Returns:
                The audio data as a bytes object
        """
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def __iter__(self):
        # A generator that outputs audio chunks.
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            self.all_data.append(chunk)

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                    self.all_data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


if __name__ == "__main__":
    import time
    with MicrophoneStream(output_file="tmp.wav") as stream:
        print("Recording")
        start_time = time.time()
        for content in stream:
            if time.time() - start_time > 5:
                break
        print("Done")
