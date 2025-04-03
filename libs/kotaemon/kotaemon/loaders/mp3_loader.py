from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from loguru import logger

from kotaemon.base import Document, Param

from .base import BaseReader

if TYPE_CHECKING:
    from transformers import pipeline


class MP3Reader(BaseReader):
    model_name_or_path: str = Param(
        help="The model name or path to use for speech recognition.",
        default="distil-whisper/distil-large-v3",
    )
    cache_dir: str = Param(
        help="The cache directory to use for the model.",
        default="models",
    )

    @Param.auto()
    def asr_pipeline(self) -> "pipeline":
        """Setup the ASR pipeline for speech recognition"""
        try:
            import accelerate  # noqa: F401
            import torch
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
        except ImportError:
            raise ImportError(
                "Please install the required packages to use the MP3Reader: "
                "'pip install accelerate torch transformers'"
            )

        try:
            # Device and model configuration
            torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            device = "cuda:0" if torch.cuda.is_available() else "cpu"

            # Model and processor initialization
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_name_or_path,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
                cache_dir=self.cache_dir,
            ).to(device)

            processor = AutoProcessor.from_pretrained(
                self.model_name_or_path,
            )

            # ASR pipeline setup
            asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                max_new_tokens=128,
                torch_dtype=torch_dtype,
                device=device,
                return_timestamps=True,
            )
            logger.info("ASR pipeline setup successful.")
        except Exception as e:
            logger.error(f"Error occurred during ASR pipeline setup: {e}")
            raise

        return asr_pipeline

    def speech_to_text(self, audio_path: str) -> str:
        try:
            import librosa

            # Performing speech recognition
            audio_array, _ = librosa.load(audio_path, sr=16000)  # 16kHz sampling rate
            result = self.asr_pipeline(audio_array)

            text = result.get("text", "").strip()
            if text == "":
                logger.warning("No text found in the audio file.")
            return text
        except Exception as e:
            logger.error(f"Error occurred during speech recognition: {e}")
            return ""

    def run(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        return self.load_data(str(file_path), extra_info=extra_info, **kwargs)

    def load_data(
        self, audio_file: str, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        # Get text from the audio file
        text = self.speech_to_text(audio_file)
        metadata = extra_info or {}

        return [Document(text=text, metadata=metadata)]
