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
from google.cloud import texttospeech
from google.oauth2 import service_account


class TTSClient:
    def __init__(self, tts_private_key_path="../keys/tts-private-key.json", tmp_output_dir="../temp/tts_temp"):
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

        # Cleanup and create temporary output directory
        self.tmp_output_dir = tmp_output_dir
        if os.path.exists(self.tmp_output_dir):
            shutil.rmtree(tmp_output_dir)
        os.makedirs(self.tmp_output_dir)
        self.file_idx = 0

    def text_to_speech(self, text):
        synthesis_input = texttospeech.SynthesisInput(text=text)
        try:
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=self.voice, audio_config=self.audio_config
            )
            file_path = os.path.join(self.tmp_output_dir, f"{self.file_idx:03}.wav")
            with open(file_path, "wb") as out:
                out.write(response.audio_content)
                # print(f'Audio content written to file "{file_path}"')
            self.file_idx += 1
            playsound.playsound(file_path)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    tts_client = TTSClient()
    tts_client.text_to_speech("Sup gang how's it hanging?")
