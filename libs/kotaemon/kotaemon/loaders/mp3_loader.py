from loguru import logger
from typing import Optional, List
from kotaemon.base import Document, BaseReader

###--------------------------------------------------------------------------###

try:
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
except ImportError:
    raise ImportError(
        "Please install the required packages: 'pip install torch transformers'"
    )


###--------------------------------------------------------------------------###


class MP3Reader(BaseReader):
    def __init__(
        self,
        model_id: str = "distil-whisper/distil-large-v3",
        cache_dir: str = "models",
    ):
        try:
            # Device and model configuration
            self.torch_dtype = (
                torch.float16 if torch.cuda.is_available() else torch.float32
            )
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

            # Model and processor initialization
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
                cache_dir=cache_dir,
            ).to(self.device)

            self.processor = AutoProcessor.from_pretrained(model_id)

            # ASR pipeline setup
            self.asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                max_new_tokens=128,
                torch_dtype=self.torch_dtype,
                device=self.device,
            )
            logger.info("ASR pipeline setup successful.")
        except Exception as e:
            logger.error(f"Error occurred during ASR pipeline setup: {e}")
            raise

    def speech_to_text(self, audio_path: str) -> str:
        try:
            # Performing speech recognition
            result = self.asr_pipeline(audio_path)
            return result.get("text", "Error: Text not found in the result")
        except Exception as e:
            logger.error(f"Error occurred during speech recognition: {e}")
            return "Error: Speech recognition failed"

    def load_data(
        self, audio_file: str, extra_info: Optional[dict] = None
    ) -> List[Document]:
        try:
            # Get text from the audio file
            text = self.speech_to_text(audio_file)

            metadata = extra_info or {}

            return [Document(text=text, metadata=metadata)]
        except Exception as e:
            logger.error(f"Error occurred while loading data: {e}")
            return []
