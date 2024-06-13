"""
Notes: 
----------------------------------------
* Right now the function takes in the filename, this could change depending on structure of final code
* Outputs to a specified file as a .wav file
* Key file is explicitly written, this should be changed
* Doesn't return path to file, this could be changed depending on final code
"""
import shutil

import playsound
import os
import logging
from google.cloud import texttospeech
from google.oauth2 import service_account
from google.api_core.retry import Retry
from utils import is_gcs_retryable


class TTSClient:
    def __init__(self, tts_private_key_path="../keys/tts-private-key.json", output_dir=None, logger=None):
        # Google Cloud client API
        assert os.path.exists(tts_private_key_path), f"TTS private key file at {tts_private_key_path} does not exist."
        credentials = service_account.Credentials.from_service_account_file(tts_private_key_path)
        self.client = texttospeech.TextToSpeechClient(credentials=credentials)

        # TTS config
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", name="en-US-Journey-F", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        self.logger = logger
        if not self.logger:
            self.logger = logging.getLogger(__name__)
        self.output_dir = output_dir
        self.file_idx = 0
        # If retrying, wait for 0.5 seconds, then keep retrying with duration * 2 (max of 4 seconds between retry)
        self.gcs_retry_policy = Retry(predicate=is_gcs_retryable, initial=0.5, maximum=4, timeout=60)

    def text_to_speech(self, text):
        # Handle empty input
        if not text.strip():
            self.logger.debug("Empty TTS input")
            return
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(
            input=synthesis_input, voice=self.voice, audio_config=self.audio_config,
            retry=self.gcs_retry_policy
        )
        file_path = os.path.join(self.output_dir, f"{self.file_idx:03}.wav")
        with open(file_path, "wb") as out:
            out.write(response.audio_content)
            if self.logger:
                self.logger.debug(f'Audio content written to file "{file_path}"')
        self.file_idx += 1
        playsound.playsound(file_path)


if __name__ == "__main__":
    tts_client = TTSClient(output_dir="tmp")
    tts_client.text_to_speech("")
    tts_client.text_to_speech("Nice try! Keep thinking about what a magnifying glass helps us do.")
