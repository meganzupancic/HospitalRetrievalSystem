"""
Advanced Testing Examples for Whisper Test System

This file contains examples for:
1. Batch testing with predefined phrases
2. Testing from audio files
3. Accuracy metrics calculation
4. Custom confidence threshold testing
"""

import json

import numpy as np
import whisper
from whisper_test import KeywordMatcher, WhisperTranscriber, load_medical_supplies

# ============================================================================
# EXAMPLE 1: Batch Testing with Predefined Phrases
# ============================================================================


def batch_test_with_phrases():
    """
    Test with a predefined list of phrases instead of microphone input.
    Useful for consistent testing and benchmarking.
    """
    test_phrases = [
        "I need band aids",
        "Give me gauze pads",
        "Can I have a thermometer",
        "I need some scissors",
        "Let me get some face masks",
        "Can you get the tweezers",
        "I'll take some antiseptic wipes",
        "Can I get elastic bandages",
        "Let me have some cold pack",
        "I need some pain reliever",
    ]

    print("\n" + "=" * 60)
    print("BATCH TESTING WITH PREDEFINED PHRASES")
    print("=" * 60)

    medical_supplies = load_medical_supplies()
    keywords = list(medical_supplies.keys())
    matcher = KeywordMatcher(keywords)

    results = []

    for idx, phrase in enumerate(test_phrases, 1):
        print(f'\nTest {idx}: "{phrase}"')

        matches = matcher.find_matches(phrase)
        if matches:
            top_match = matches[0]
            print(
                f"✓ Match: {top_match['keyword']} ({top_match['confidence']:.0f}% confidence)"
            )
            location_data = medical_supplies[top_match["keyword"]]
            print(
                f"  📍 Rack {location_data['rack']}, Location {location_data['location']}"
            )
        else:
            print("✗ No match found")

        results.append(
            {
                "phrase": phrase,
                "matched": len(matches) > 0,
                "match_count": len(matches),
                "top_match": matches[0]["keyword"] if matches else None,
                "confidence": matches[0]["confidence"] if matches else 0,
            }
        )

    # Calculate accuracy
    successful = sum(1 for r in results if r["matched"])
    accuracy = (successful / len(results)) * 100
    avg_confidence = np.mean([r["confidence"] for r in results if r["matched"]])

    print(f"\n{'='*60}")
    print("BATCH TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total phrases: {len(results)}")
    print(f"Successful matches: {successful}/{len(results)} ({accuracy:.1f}%)")
    print(f"Average confidence: {avg_confidence:.1f}%")

    return results


# ============================================================================
# EXAMPLE 2: Testing from Audio File
# ============================================================================


def test_from_audio_file(audio_file_path):
    """
    Test transcription from an existing audio file instead of recording.
    Useful for consistent testing with the same audio samples.

    Usage:
        results = test_from_audio_file("sample_audio.wav")
    """
    import librosa

    print(f"\n{'='*60}")
    print(f"TESTING FROM AUDIO FILE: {audio_file_path}")
    print(f"{'='*60}\n")

    # Load audio file
    try:
        audio_data, sr = librosa.load(audio_file_path, sr=16000)
        print(f"✓ Loaded audio file ({len(audio_data)/16000:.1f} seconds)")
    except Exception as e:
        print(f"❌ Error loading audio file: {e}")
        return None

    # Transcribe
    transcriber = WhisperTranscriber()
    print("\n📝 Transcribing...")
    result = transcriber.transcribe(audio_data)

    if result is None:
        return None

    transcription = result["text"].strip()
    print(f'Transcription: "{transcription}"')

    # Match keywords
    medical_supplies = load_medical_supplies()
    keywords = list(medical_supplies.keys())
    matcher = KeywordMatcher(keywords)

    matches = matcher.find_matches(transcription)

    if matches:
        print(f"\n✓ Found {len(matches)} match(es):")
        for i, match in enumerate(matches, 1):
            keyword = match["keyword"]
            location_data = medical_supplies[keyword]
            print(
                f"  [{i}] '{match['word']}' → '{keyword}' ({match['confidence']:.0f}%)"
            )
            print(
                f"       📍 Rack {location_data['rack']}, Location {location_data['location']}"
            )
    else:
        print("\n✗ No matches found")

    return {"file": audio_file_path, "transcription": transcription, "matches": matches}


# ============================================================================
# EXAMPLE 3: Test Different Confidence Thresholds
# ============================================================================


def test_confidence_thresholds(transcription_text):
    """
    Test the same transcription against multiple confidence thresholds
    to understand the impact of threshold settings.

    Usage:
        test_confidence_thresholds("I need some band aids")
    """
    print(f"\n{'='*60}")
    print("CONFIDENCE THRESHOLD TESTING")
    print(f"Testing: '{transcription_text}'")
    print(f"{'='*60}\n")

    medical_supplies = load_medical_supplies()
    keywords = list(medical_supplies.keys())

    thresholds = [60, 70, 80, 90, 95, 100]
    results_by_threshold = {}

    for threshold in thresholds:
        matcher = KeywordMatcher(keywords, threshold=threshold)
        matches = matcher.find_matches(transcription_text)
        results_by_threshold[threshold] = matches

        match_count = len(matches)
        top_confidence = matches[0]["confidence"] if matches else 0

        print(
            f"Threshold {threshold}%: {match_count} match(es) "
            + (
                f"(top: {matches[0]['keyword']} @ {top_confidence:.0f}%)"
                if matches
                else "(none)"
            )
        )

    print(f"\n{'='*60}")
    print("ANALYSIS:")
    print("- Lower threshold = more matches but more false positives")
    print("- Higher threshold = fewer matches but higher accuracy")
    print("- Recommended: 80% (good balance)")

    return results_by_threshold


# ============================================================================
# EXAMPLE 4: Accuracy Metrics from Results File
# ============================================================================


def analyze_test_results(results_file="test_results.json"):
    """
    Analyze existing test_results.json file and calculate accuracy metrics.
    """
    try:
        with open(results_file, "r") as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"Error: {results_file} not found")
        return None

    print(f"\n{'='*60}")
    print(f"TEST RESULTS ANALYSIS: {results_file}")
    print(f"{'='*60}\n")

    total_tests = len(results)
    successful = sum(1 for r in results if r.get("matched_item"))
    failed = total_tests - successful

    print(f"Total Tests: {total_tests}")
    print(f"Successful Matches: {successful}")
    print(f"Failed Matches: {failed}")
    print(f"Match Accuracy: {(successful/total_tests*100):.1f}%")

    # Find patterns in failures
    if failed > 0:
        print("\nFailed transcriptions:")
        for r in results:
            if not r.get("matched_item"):
                print(f"  - \"{r.get('transcription')}\"")

    # Save analysis
    analysis = {
        "total_tests": total_tests,
        "successful_matches": successful,
        "failed_matches": failed,
        "match_accuracy_percent": (successful / total_tests * 100),
        "analysis_timestamp": str(pd.Timestamp.now()),
    }

    with open("results_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    print("\nAnalysis saved to: results_analysis.json")
    return analysis


# ============================================================================
# EXAMPLE 5: Simulate Different Whisper Models
# ============================================================================


def compare_whisper_models(audio_data, sample_rate=16000):
    """
    Test the same audio with different Whisper models and compare results.
    WARNING: This requires downloading all models (~3GB total)

    Usage:
        # Record or load audio first
        results = compare_whisper_models(audio_data)
    """
    models = ["tiny", "base", "small", "medium"]

    print(f"\n{'='*60}")
    print("COMPARING WHISPER MODELS")
    print(f"{'='*60}\n")

    import time

    results = {}

    for model_name in models:
        print(f"Testing {model_name} model...")
        start_time = time.time()

        try:
            model = whisper.load_model(model_name)
            result = model.transcribe(audio_data, language="en", verbose=False)
            elapsed = time.time() - start_time

            results[model_name] = {
                "transcription": result["text"].strip(),
                "time_seconds": elapsed,
            }

            print(f"  ✓ \"{result['text'].strip()}\" ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n{'='*60}")
    print("COMPARISON:")
    for model_name, result in results.items():
        print(f"\n{model_name.upper()}:")
        print(f"  Transcription: {result['transcription']}")
        print(f"  Time: {result['time_seconds']:.1f} seconds")

    return results


# ============================================================================
# EXAMPLE 6: Generate Detailed Test Report
# ============================================================================


def generate_test_report(
    results_file="test_results.json", output_file="test_report.html"
):
    """
    Generate a detailed HTML report of test results with charts and statistics.
    """
    import json
    from datetime import datetime

    try:
        with open(results_file, "r") as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"Error: {results_file} not found")
        return

    # Calculate statistics
    total = len(results)
    successful = sum(1 for r in results if r.get("matched_item"))
    accuracy = (successful / total * 100) if total > 0 else 0

    # HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Whisper Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; color: #333; }}
            .stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0; }}
            .stat {{ background: #f0f0f0; padding: 15px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #667eea; color: white; }}
            .success {{ background: #d4edda; }}
            .failure {{ background: #f8d7da; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Whisper Test Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat">
                <div class="stat-value">{successful}</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat">
                <div class="stat-value">{accuracy:.1f}%</div>
                <div class="stat-label">Accuracy</div>
            </div>
        </div>
        
        <table>
            <tr>
                <th>Test #</th>
                <th>Transcription</th>
                <th>Matched Item</th>
                <th>Status</th>
            </tr>
    """

    for r in results:
        status = "✓ Success" if r.get("matched_item") else "✗ Failed"
        status_class = "success" if r.get("matched_item") else "failure"

        html_content += f"""
            <tr class="{status_class}">
                <td>{r.get('test_number')}</td>
                <td>"{r.get('transcription')}"</td>
                <td>{r.get('matched_item', 'N/A')}</td>
                <td>{status}</td>
            </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Report saved to: {output_file}")


# ============================================================================
# MAIN MENU
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("WHISPER TEST SYSTEM - ADVANCED EXAMPLES")
    print("=" * 60)
    print("\nAvailable examples:")
    print("1. Batch testing with predefined phrases")
    print("2. Test from audio file")
    print("3. Test different confidence thresholds")
    print("4. Analyze existing test results")
    print("5. Compare Whisper models")
    print("6. Generate HTML test report")
    print("\nNote: These are reference examples.")
    print("Modify and run individual functions as needed.")
    print("=" * 60)

    # Example: Run batch testing
    # results = batch_test_with_phrases()

    # Example: Test from file
    # results = test_from_audio_file("your_audio.wav")

    # Example: Analyze results
    # analysis = analyze_test_results("test_results.json")

    # Example: Generate report
    # generate_test_report()
