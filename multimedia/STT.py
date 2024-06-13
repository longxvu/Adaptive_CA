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

from google.cloud import speech
from google.oauth2 import service_account
from .audio_recorder import MicRecorder
from .microphone import MicrophoneStream
from google.cloud.speech_v2.types import cloud_speech
import google.cloud.speech_v2 as speech_v2
from google.protobuf import duration_pb2
from datetime import datetime
import time


class STTClient:
    def __init__(self, stt_private_key_path="../keys/stt-private-key.json", sample_frequency=24000, max_alternatives=3,
                 output_dir=None, logger=None):
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

        self.audio_recorder = MicRecorder(sample_frequency, output_dir, logger)

    def get_speech_text_from_file(self, file_path):
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
        responses = self.client.recognize(config=self.stt_config, audio=audio)
        results = []
        for result in responses.results:
            results.append(result.alternatives[0].transcript)
        return results[0] if results else ""

    def speech_to_text(self, duration=5):
        speech_file_path = self.audio_recorder.record(duration)
        text = self.get_speech_text_from_file(speech_file_path)
        return text


class STTStreamingClient:
    def __init__(self, gcs_private_key_path="../keys/stt-private-key.json", gcs_project_id="emerald-trilogy-422704-h7",
                 sample_frequency=16000, channel_count=1, max_start_timeout=15, max_pause_duration=5, output_dir=None,
                 logger=None):
        credentials = service_account.Credentials.from_service_account_file(gcs_private_key_path)
        self.client = speech_v2.SpeechClient(credentials=credentials)
        self.project_id = gcs_project_id
        self.rate = sample_frequency
        self.audio_channels = channel_count
        self._init_cloud_recognizer(max_start_timeout, max_pause_duration)

        self.output_dir = output_dir
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
        self.logger = logger

    def _init_cloud_recognizer(self, max_start_timeout, max_pause_duration):
        # Audio and recognition config. Should be the same as the one in microphone.py
        recognition_config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.rate,
                audio_channel_count=self.audio_channels,
            ),
            language_codes=["en-US"],
            model="long",
            features=cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True
            )
        )
        # Voice activity timeout events
        speech_start_timeout = duration_pb2.Duration(seconds=max_start_timeout)
        speech_end_timeout = duration_pb2.Duration(seconds=max_pause_duration)
        voice_activity_timeout = (
            cloud_speech.StreamingRecognitionFeatures.VoiceActivityTimeout(
                speech_start_timeout=speech_start_timeout, speech_end_timeout=speech_end_timeout
            )
        )

        streaming_features = cloud_speech.StreamingRecognitionFeatures(
            enable_voice_activity_events=True, voice_activity_timeout=voice_activity_timeout
        )
        # Config for streaming audio + timeout events
        streaming_config = cloud_speech.StreamingRecognitionConfig(
            config=recognition_config, streaming_features=streaming_features
        )

        # Save config requests to reuse later
        self.config_request = cloud_speech.StreamingRecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/global/recognizers/_", streaming_config=streaming_config
        )

    def _streaming_requests(self, audio):
        yield self.config_request
        yield from audio

    def speech_to_text(self):
        recording_output_file = None
        if self.output_dir:
            recording_output_file = os.path.join(self.output_dir, f"{datetime.now().strftime('%y-%m-%d_%H-%M-%S')}.wav")
        if self.logger:
            self.logger.debug(f"Recording audio to {recording_output_file}")
            self.logger.debug("Listening...")
        else:
            print("Listening...")

        with MicrophoneStream(channels=self.audio_channels, rate=self.rate, output_file=recording_output_file) as audio_stream:
            audio_requests = (
                cloud_speech.StreamingRecognizeRequest(audio=content) for content in audio_stream
            )
            responses_iterator = self.client.streaming_recognize(requests=self._streaming_requests(audio_requests))
            responses = []
            for response in responses_iterator:
                # if (response.speech_event_type
                #         == cloud_speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_BEGIN):
                #     print("Speech started.")
                # if (response.speech_event_type
                #         == cloud_speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_END):
                #     print("Speech ended.")
                for result in response.results:
                    if "alternatives" in result:
                        responses.append(result.alternatives[0].transcript)

            return "".join(responses)


if __name__ == "__main__":
    stt_client = STTStreamingClient()
    speech_text = stt_client.speech_to_text()
    print(speech_text)
