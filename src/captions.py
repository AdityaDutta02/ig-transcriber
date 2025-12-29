"""
Captions Module

Generates SRT subtitle files from transcription segments.
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import timedelta


class CaptionGenerator:
    """
    Generates captions and SRT files from transcription segments.

    Features:
    - Configurable words per line
    - Configurable number of lines per caption
    - Proper SRT formatting with timestamps
    - Handles multiple languages
    """

    def __init__(self, words_per_line: int = 10, max_lines: int = 2):
        """
        Initialize caption generator.

        Args:
            words_per_line: Maximum words per line (default: 10)
            max_lines: Maximum lines per caption (default: 2)
        """
        self.words_per_line = max(1, min(words_per_line, 20))  # 1-20 words
        self.max_lines = max(1, min(max_lines, 3))  # 1-3 lines
        self.words_per_caption = self.words_per_line * self.max_lines

    def format_timestamp(self, seconds: float) -> str:
        """
        Format seconds to SRT timestamp format (HH:MM:SS,mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def split_into_lines(self, words: List[str]) -> List[str]:
        """
        Split words into lines based on words_per_line.

        Args:
            words: List of words

        Returns:
            List of lines (strings)
        """
        lines = []
        for i in range(0, len(words), self.words_per_line):
            line = " ".join(words[i:i + self.words_per_line])
            lines.append(line)
        return lines

    def generate_captions(self, segments: List[Dict]) -> List[Dict]:
        """
        Generate caption entries from transcription segments.

        Args:
            segments: List of segment dictionaries with 'start', 'end', 'text'

        Returns:
            List of caption dictionaries with 'index', 'start', 'end', 'text'
        """
        captions = []
        caption_index = 1

        current_words = []
        current_start = None
        current_end = None

        for segment in segments:
            # Extract words from segment
            words = segment['text'].strip().split()

            if not words:
                continue

            if current_start is None:
                current_start = segment['start']

            current_words.extend(words)
            current_end = segment['end']

            # Check if we have enough words for a caption
            if len(current_words) >= self.words_per_caption:
                # Take words for this caption
                caption_words = current_words[:self.words_per_caption]
                remaining_words = current_words[self.words_per_caption:]

                # Create lines
                lines = self.split_into_lines(caption_words)
                text = "\n".join(lines[:self.max_lines])

                # Add caption
                captions.append({
                    'index': caption_index,
                    'start': current_start,
                    'end': current_end,
                    'text': text
                })

                caption_index += 1
                current_words = remaining_words
                current_start = current_end if remaining_words else None

        # Add remaining words as final caption
        if current_words and current_start is not None:
            lines = self.split_into_lines(current_words)
            text = "\n".join(lines[:self.max_lines])

            captions.append({
                'index': caption_index,
                'start': current_start,
                'end': current_end,
                'text': text
            })

        return captions

    def generate_srt(self, segments: List[Dict]) -> str:
        """
        Generate SRT format string from transcription segments.

        Args:
            segments: List of segment dictionaries with 'start', 'end', 'text'

        Returns:
            SRT formatted string
        """
        captions = self.generate_captions(segments)

        srt_lines = []
        for caption in captions:
            # Caption index
            srt_lines.append(str(caption['index']))

            # Timestamps
            start_time = self.format_timestamp(caption['start'])
            end_time = self.format_timestamp(caption['end'])
            srt_lines.append(f"{start_time} --> {end_time}")

            # Caption text
            srt_lines.append(caption['text'])

            # Blank line between captions
            srt_lines.append("")

        return "\n".join(srt_lines)

    def save_srt(self, segments: List[Dict], output_path: Path) -> Path:
        """
        Save SRT file from transcription segments.

        Args:
            segments: List of segment dictionaries
            output_path: Path to save SRT file

        Returns:
            Path to saved file
        """
        srt_content = self.generate_srt(segments)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write SRT file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        return output_path

    def generate_vtt(self, segments: List[Dict]) -> str:
        """
        Generate WebVTT format string from transcription segments.

        Args:
            segments: List of segment dictionaries

        Returns:
            WebVTT formatted string
        """
        captions = self.generate_captions(segments)

        vtt_lines = ["WEBVTT", ""]

        for caption in captions:
            # Timestamps (VTT uses . instead of , for milliseconds)
            start_time = self.format_timestamp(caption['start']).replace(',', '.')
            end_time = self.format_timestamp(caption['end']).replace(',', '.')
            vtt_lines.append(f"{start_time} --> {end_time}")

            # Caption text
            vtt_lines.append(caption['text'])

            # Blank line between captions
            vtt_lines.append("")

        return "\n".join(vtt_lines)

    def save_vtt(self, segments: List[Dict], output_path: Path) -> Path:
        """
        Save WebVTT file from transcription segments.

        Args:
            segments: List of segment dictionaries
            output_path: Path to save VTT file

        Returns:
            Path to saved file
        """
        vtt_content = self.generate_vtt(segments)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write VTT file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(vtt_content)

        return output_path


def generate_srt_from_segments(
    segments: List[Dict],
    output_path: Path,
    words_per_line: int = 10,
    max_lines: int = 2
) -> Path:
    """
    Convenience function to generate SRT file.

    Args:
        segments: List of transcription segments
        output_path: Path to save SRT file
        words_per_line: Words per line (1-20)
        max_lines: Lines per caption (1-3)

    Returns:
        Path to saved SRT file

    Example:
        >>> segments = [
        ...     {'start': 0.0, 'end': 2.5, 'text': 'Hello world'},
        ...     {'start': 2.5, 'end': 5.0, 'text': 'This is a test'}
        ... ]
        >>> srt_path = generate_srt_from_segments(segments, Path('output.srt'))
    """
    generator = CaptionGenerator(words_per_line, max_lines)
    return generator.save_srt(segments, output_path)


def generate_vtt_from_segments(
    segments: List[Dict],
    output_path: Path,
    words_per_line: int = 10,
    max_lines: int = 2
) -> Path:
    """
    Convenience function to generate WebVTT file.

    Args:
        segments: List of transcription segments
        output_path: Path to save VTT file
        words_per_line: Words per line (1-20)
        max_lines: Lines per caption (1-3)

    Returns:
        Path to saved VTT file
    """
    generator = CaptionGenerator(words_per_line, max_lines)
    return generator.save_vtt(segments, output_path)


# Testing
if __name__ == "__main__":
    # Example segments
    test_segments = [
        {'start': 0.0, 'end': 2.5, 'text': 'Hello world this is a test'},
        {'start': 2.5, 'end': 5.0, 'text': 'of the caption generation system'},
        {'start': 5.0, 'end': 8.0, 'text': 'it should split text into lines properly'},
        {'start': 8.0, 'end': 10.0, 'text': 'and create proper timestamps'},
    ]

    # Test different configurations
    print("=" * 70)
    print("SRT Caption Generator - Test")
    print("=" * 70)
    print()

    # Test 1: 5 words per line, 2 lines
    print("Test 1: 5 words per line, 2 lines")
    print("-" * 70)
    generator = CaptionGenerator(words_per_line=5, max_lines=2)
    srt_content = generator.generate_srt(test_segments)
    print(srt_content)
    print()

    # Test 2: 10 words per line, 1 line
    print("Test 2: 10 words per line, 1 line")
    print("-" * 70)
    generator = CaptionGenerator(words_per_line=10, max_lines=1)
    srt_content = generator.generate_srt(test_segments)
    print(srt_content)
    print()

    # Test 3: WebVTT format
    print("Test 3: WebVTT format")
    print("-" * 70)
    vtt_content = generator.generate_vtt(test_segments)
    print(vtt_content)
