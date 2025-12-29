"""
Transcriber Module

Handles audio transcription using Faster-Whisper with GPU acceleration.
Processes audio files from downloader and generates text transcriptions.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch

from loguru import logger
from tqdm import tqdm

from config import TranscriptionConfig
from utils import ensure_directory, format_duration


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class ReelTranscriber:
    """
    Transcribes audio using Faster-Whisper (CTranslate2-based implementation).

    Features:
    - GPU acceleration (CUDA)
    - Automatic language detection
    - Multi-language support (English, Hindi, 99+ languages)
    - Faster inference with CTranslate2
    - VAD (Voice Activity Detection) filtering
    - Progress tracking
    - Error handling
    """

    def __init__(self, config: TranscriptionConfig):
        """
        Initialize transcriber.

        Args:
            config: Transcription configuration
        """
        self.config = config
        self.model = None
        self.device = None

        # Check if Faster-Whisper is available
        if not self._check_whisper():
            raise RuntimeError("faster-whisper is not installed. Install with: pip install faster-whisper")

        # Load model
        self._load_model()

        logger.info("Transcriber initialized")
        logger.info(f"Model: {config.model}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Compute type: {self.config.compute_type}")
        logger.info(f"Language: {config.language}")

    def _check_whisper(self) -> bool:
        """Check if Faster-Whisper is available."""
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False

    def _load_model(self) -> None:
        """Load Faster-Whisper model."""
        from faster_whisper import WhisperModel

        logger.info(f"Loading Faster-Whisper model: {self.config.model}")

        # Determine device
        if self.config.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = self.config.device

        # Validate device
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"

        # Adjust compute_type based on device
        compute_type = self.config.compute_type
        if self.device == "cpu":
            # CPU doesn't support float16, use int8 or float32
            if compute_type == "float16":
                compute_type = "int8"
                logger.info("Adjusted compute_type to 'int8' for CPU")

        # Load model
        try:
            start_time = time.time()
            self.model = WhisperModel(
                self.config.model,
                device=self.device,
                compute_type=compute_type,
                download_root=None,  # Use default cache
                num_workers=1  # Number of workers for parallel processing
            )
            load_time = time.time() - start_time

            logger.info(f"Model loaded in {load_time:.2f}s")

            # Log GPU info if using CUDA
            if self.device == "cuda":
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                logger.info(f"GPU: {gpu_name}")
                logger.info(f"GPU Memory: {gpu_memory:.1f} GB")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise TranscriptionError(f"Failed to load Faster-Whisper model: {e}")
    
    def transcribe_audio(
        self,
        audio_file: Path,
        language: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict], Optional[str]]:
        """
        Transcribe a single audio file.

        Args:
            audio_file: Path to audio file
            language: Optional language override (e.g., "en", "hi")

        Returns:
            Tuple of (success, transcription_text, metadata, error_message)
        """
        if not audio_file.exists():
            return False, None, None, f"Audio file not found: {audio_file}"

        try:
            start_time = time.time()

            # Determine language
            lang = language or self.config.language
            if lang == "auto":
                lang = None  # Let Whisper auto-detect

            # Transcribe using faster-whisper
            # Note: faster-whisper returns (segments, info) tuple
            logger.debug(f"Transcribing: {audio_file.name}")

            segments, info = self.model.transcribe(
                str(audio_file),
                language=lang,
                task="transcribe",
                beam_size=self.config.beam_size,
                best_of=self.config.best_of,
                temperature=self.config.temperature,
                condition_on_previous_text=self.config.condition_on_previous_text,
                vad_filter=self.config.vad_filter,
                vad_parameters=None  # Use default VAD parameters
            )

            processing_time = time.time() - start_time

            # Extract transcription from segments
            # Note: segments is a generator in faster-whisper
            segments_list = list(segments)
            transcription = " ".join(segment.text for segment in segments_list).strip()

            # Get detected language from info
            detected_language = info.language if hasattr(info, 'language') else "unknown"

            # Calculate confidence from segments
            if segments_list:
                # faster-whisper provides avg_logprob and no_speech_prob per segment
                avg_confidence = sum(
                    1.0 - segment.no_speech_prob
                    for segment in segments_list
                    if hasattr(segment, 'no_speech_prob')
                ) / len(segments_list) if segments_list else None
            else:
                avg_confidence = None

            # Get duration from info
            duration = info.duration if hasattr(info, 'duration') else 0

            # Convert segments to dictionary format for caption generation
            segments_data = [
                {
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                }
                for segment in segments_list
            ]

            # Metadata
            metadata = {
                "language": detected_language,
                "duration": duration,
                "processing_time": processing_time,
                "confidence": avg_confidence,
                "segments_count": len(segments_list),
                "segments": segments_data  # Include segments for caption generation
            }

            logger.debug(f"Transcribed {audio_file.name} in {processing_time:.2f}s")
            logger.debug(f"Language: {detected_language}, Length: {len(transcription)} chars")

            return True, transcription, metadata, None

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(f"{audio_file.name}: {error_msg}")
            return False, None, None, error_msg
    
    def transcribe_batch(
        self,
        audio_records: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe multiple audio files.
        
        Args:
            audio_records: List of records with 'audio_file' key
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (successful_transcriptions, failed_transcriptions)
        """
        successful = []
        failed = []
        
        logger.info(f"Starting batch transcription of {len(audio_records)} audio files")
        logger.info(f"Model: {self.config.model}, Device: {self.device}")
        
        # Create progress bar
        with tqdm(total=len(audio_records), desc="Transcribing audio", unit="file") as pbar:
            for record in audio_records:
                try:
                    audio_file = Path(record['audio_file'])
                    
                    # Transcribe
                    success, transcription, metadata, error = self.transcribe_audio(audio_file)
                    
                    if success:
                        result = {
                            **record,
                            'transcription': transcription,
                            'transcription_metadata': metadata,
                            'transcription_success': True
                        }
                        successful.append(result)
                        logger.debug(f"Success: {record['reel_id']}")
                    else:
                        result = {
                            **record,
                            'transcription_success': False,
                            'error': error
                        }
                        failed.append(result)
                        logger.warning(f"Failed: {record['reel_id']} - {error}")
                    
                    # Update progress
                    pbar.update(1)
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(len(successful) + len(failed), len(audio_records))
                
                except Exception as e:
                    logger.error(f"Unexpected error transcribing {record.get('reel_id', 'unknown')}: {e}")
                    failed.append({
                        **record,
                        'transcription_success': False,
                        'error': str(e)
                    })
                    pbar.update(1)
        
        logger.info(f"Batch transcription complete: {len(successful)} successful, {len(failed)} failed")
        
        return successful, failed
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models."""
        # faster-whisper supports the same model names as openai-whisper
        return ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2", "large-v3", "large"]
    
    def get_device_info(self) -> Dict:
        """Get information about the device being used."""
        info = {
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
        }
        
        if torch.cuda.is_available():
            info.update({
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory / (1024**3),
                "gpu_memory_allocated": torch.cuda.memory_allocated(0) / (1024**3),
                "gpu_memory_reserved": torch.cuda.memory_reserved(0) / (1024**3),
            })
        
        return info


def transcribe_audio_files(
    audio_records: List[Dict],
    config: Optional[TranscriptionConfig] = None,
    progress_callback: Optional[callable] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Convenience function to transcribe audio files.
    
    Args:
        audio_records: List of records with 'audio_file' key
        config: Optional transcription configuration
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (successful_transcriptions, failed_transcriptions)
        
    Example:
        >>> from downloader import download_reels
        >>> successful_downloads, _ = download_reels(urls)
        >>> successful_transcriptions, _ = transcribe_audio_files(successful_downloads)
        >>> print(f"Transcribed: {len(successful_transcriptions)}")
    """
    if config is None:
        from config import load_config
        config = load_config().transcription
    
    transcriber = ReelTranscriber(config)
    return transcriber.transcribe_batch(audio_records, progress_callback)


# Testing and example usage
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import load_config
    
    print("=" * 70)
    print("Transcriber Module - Test Mode")
    print("=" * 70)
    print()
    
    # Test 1: Check Faster-Whisper availability
    print("Test 1: Checking Faster-Whisper availability...")
    try:
        from faster_whisper import WhisperModel
        print("[OK] Faster-Whisper is installed")
        print("  Available models: tiny, base, small, medium, large")
    except ImportError:
        print("[ERROR] Faster-Whisper is not installed")
        print("  Install with: pip install faster-whisper")
        sys.exit(1)

    print()

    # Test 2: Check CUDA availability
    print("Test 2: Checking CUDA availability...")
    if torch.cuda.is_available():
        print("[OK] CUDA is available")
        print(f"  Device: {torch.cuda.get_device_name(0)}")
        print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")
    else:
        print("[WARNING] CUDA not available (will use CPU)")
        print("  Transcription will be slower without GPU")

    print()

    # Test 3: Initialize transcriber
    print("Test 3: Initializing transcriber...")
    try:
        config = load_config()
        transcriber = ReelTranscriber(config.transcription)
        print("[OK] Transcriber initialized successfully")
        print(f"  Model: {config.transcription.model}")
        print(f"  Device: {transcriber.device}")
        print(f"  Compute type: {config.transcription.compute_type}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize: {e}")
        sys.exit(1)
    
    print()
    
    # Test 4: Device info
    print("Test 4: Device information...")
    device_info = transcriber.get_device_info()
    print(f"Device: {device_info['device']}")
    print(f"CUDA Available: {device_info['cuda_available']}")
    if device_info['cuda_available']:
        print(f"GPU: {device_info['gpu_name']}")
        print(f"Total Memory: {device_info['gpu_memory_total']:.1f} GB")
    
    print()
    print("=" * 70)
    print("Transcriber module test complete!")
    print("=" * 70)
    print()
    print("To test with real audio files:")
    print("1. Download some reels first (use test_download.py)")
    print("2. Run: python test_transcribe.py")
    print()

