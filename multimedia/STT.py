"""
Notes
----------------------------------------
* I think OpenAI GPT4 has a STT model builtin so this part might not be necessary
*In the future we might be able to load iterable object directly from the mic into STT instead of having a intermediary file
*Shifted it from a streaming model to fixed file model if we want to do above we have to shift back
*returns the list utterences said in the audio file
----------------------------------------
"""
import os
import shutil

from google.cloud import speech
from google.oauth2 import service_account
from .audio_recorder import MicRecorder


class STTClient:
    def __init__(self, stt_private_key_path="../keys/stt-private-key.json", sample_frequency=24000, max_alternatives=3,
                 tmp_output_dir="../temp/stt_temp"):
        # STT Client and config
        assert os.path.exists(stt_private_key_path), f"STT private key file at {stt_private_key_path} does not exist."
        credentials = service_account.Credentials.from_service_account_file(stt_private_key_path)
        self.client = speech.SpeechClient(credentials=credentials)
        self.stt_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_frequency,
            language_code="en-US",
            max_alternatives=max_alternatives,
        )

        self.audio_recorder = MicRecorder(sample_rate=sample_frequency, output_dir=tmp_output_dir)

        # Create and cleanup temporary directory output
        self.tmp_output_dir = tmp_output_dir
        if os.path.exists(self.tmp_output_dir):
            shutil.rmtree(self.tmp_output_dir)
        os.makedirs(self.tmp_output_dir)

        self.tmp_file_idx = 0

    def get_speech_text_from_file(self, file_path) -> list[str]:
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
        responses = self.client.recognize(config=self.stt_config, audio=audio)
        results = []
        for result in responses.results:
            results.append(result.alternatives[0].transcript)
        return results

    def speech_to_text(self, duration=5):
        speech_file_path = self.audio_recorder.record(duration)
        text = self.get_speech_text_from_file(speech_file_path)
        return text


if __name__ == "__main__":
    stt_client = STTClient(sample_frequency=16000)
    result = stt_client.speech_to_text(3)
    print(result)
