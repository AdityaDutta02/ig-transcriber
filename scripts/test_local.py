"""
Local Testing Script

Run this before deploying to ensure basic functionality works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from config import load_config
        from downloader import VideoDownloader
        from transcriber import ReelTranscriber
        from captions import CaptionGenerator
        from utils import validate_video_url, detect_platform
        print("  ✓ All imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from config import load_config
        config = load_config()
        assert config.transcription.model in ["tiny", "base", "small", "medium", "large"]
        assert config.transcription.device in ["cpu", "cuda", "auto"]
        print(f"  ✓ Config loaded: model={config.transcription.model}, device={config.transcription.device}")
        return True
    except Exception as e:
        print(f"  ✗ Config test failed: {e}")
        return False


def test_url_validation():
    """Test URL validation."""
    print("\nTesting URL validation...")
    try:
        from utils import validate_video_url, detect_platform

        # Test Instagram
        ig_url = "https://www.instagram.com/reel/abc123"
        assert validate_video_url(ig_url), "Instagram URL validation failed"
        assert detect_platform(ig_url) == "instagram", "Instagram platform detection failed"

        # Test YouTube
        yt_url = "https://www.youtube.com/watch?v=abc123"
        assert validate_video_url(yt_url), "YouTube URL validation failed"
        assert detect_platform(yt_url) == "youtube", "YouTube platform detection failed"

        # Test invalid
        invalid_url = "https://example.com"
        assert not validate_video_url(invalid_url), "Invalid URL should fail validation"

        print("  ✓ URL validation working")
        return True
    except Exception as e:
        print(f"  ✗ URL validation failed: {e}")
        return False


def test_caption_generator():
    """Test caption generation."""
    print("\nTesting caption generation...")
    try:
        from captions import CaptionGenerator

        # Sample segments
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello world"},
            {"start": 2.0, "end": 4.0, "text": "This is a test"}
        ]

        caption_gen = CaptionGenerator(words_per_line=5, max_lines=2)

        # Test SRT generation
        srt = caption_gen.generate_srt(segments)
        assert "00:00:00,000" in srt, "SRT timestamp missing"
        assert "Hello world" in srt, "SRT content missing"

        # Test VTT generation
        vtt = caption_gen.generate_vtt(segments)
        assert "WEBVTT" in vtt, "VTT header missing"
        assert "Hello world" in vtt, "VTT content missing"

        print("  ✓ Caption generation working")
        return True
    except Exception as e:
        print(f"  ✗ Caption generation failed: {e}")
        return False


def test_transcriber_init():
    """Test transcriber initialization."""
    print("\nTesting transcriber initialization...")
    try:
        from config import load_config
        from transcriber import ReelTranscriber

        config = load_config()
        transcriber = ReelTranscriber(config.transcription)

        print(f"  ✓ Transcriber initialized: device={transcriber.device}")
        return True
    except Exception as e:
        print(f"  ✗ Transcriber initialization failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("Running Local Tests")
    print("=" * 70)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("URL Validation", test_url_validation),
        ("Caption Generation", test_caption_generator),
        ("Transcriber Init", test_transcriber_init),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("-" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n✓ All tests passed! Safe to deploy.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Fix before deploying.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
