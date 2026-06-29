"""Text-to-speech and speech-to-text via Azure Cognitive Services Speech."""

from __future__ import annotations

import tempfile

from eva_core.config import Settings


class SpeechError(RuntimeError):
    """Raised when an Azure Speech operation fails."""


class AzureSpeech:
    """Thin wrapper around the Azure Speech SDK for TTS and STT."""

    def __init__(self, settings: Settings) -> None:
        self._key = settings.azure_speech_key
        self._region = settings.azure_speech_region
        self._voice = settings.azure_speech_voice

    def is_available(self) -> bool:
        return bool(self._key and self._region)

    def _speech_config(self):
        import azure.cognitiveservices.speech as speechsdk

        if not self.is_available():
            raise SpeechError(
                "Azure Speech is not configured (set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION)."
            )
        config = speechsdk.SpeechConfig(subscription=self._key, region=self._region)
        config.speech_synthesis_voice_name = self._voice
        return config

    def text_to_speech(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize ``text`` and return WAV audio bytes."""
        import azure.cognitiveservices.speech as speechsdk

        config = self._speech_config()
        if voice:
            config.speech_synthesis_voice_name = voice

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data)
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            raise SpeechError(f"TTS canceled: {details.reason} - {details.error_details}")
        raise SpeechError(f"TTS failed: {result.reason}")

    def speech_to_text(self, audio_bytes: bytes) -> str:
        """Transcribe WAV ``audio_bytes`` to text."""
        import azure.cognitiveservices.speech as speechsdk

        config = self._speech_config()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            audio_config = speechsdk.audio.AudioConfig(filename=tmp.name)
            recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)
            result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        if result.reason == speechsdk.ResultReason.NoMatch:
            raise SpeechError("No speech could be recognized from the audio.")
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            raise SpeechError(f"STT canceled: {details.reason} - {details.error_details}")
        raise SpeechError(f"STT failed: {result.reason}")
