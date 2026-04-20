#!/usr/bin/env python3
"""Quick test to verify STT mishearing corrections are working."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raspi_system.keyword_matcher import build_keyword_matcher
from raspi_system.medical_abbreviations import normalize_abbreviations

# Test data
test_database = [
    {"item": "syringes", "rack": 4, "location": 3},
    {"item": "latex gloves", "rack": 1, "location": 2},
    {"item": "gauze pads", "rack": 2, "location": 12},
    {"item": "1 milliliter syringe", "rack": 4, "location": 3},
    {"item": "3 milliliter syringe", "rack": 4, "location": 4},
]

print("\n" + "=" * 70)
print("TESTING PHONETIC CORRECTIONS FOR STT MISHEARINGS")
print("=" * 70)

# Test 1: Show phonetic corrections
print("\n[TEST 1] Phonetic Correction Examples:")
print("-" * 70)

mishearings = [
    "one mil leader syringe",
    "three mil peter syringe",
    "five mill letter syringe",
    "I need 10 mil leader",
]

for text in mishearings:
    corrected = normalize_abbreviations(text)
    print(f"Original:   '{text}'")
    print(f"Corrected:  '{corrected}'")
    print()

# Test 2: Keyword matching with mishearings
print("\n[TEST 2] Keyword Matching (Mishearings → Items):")
print("-" * 70)

matcher = build_keyword_matcher(test_database)

test_commands = [
    "I heard one mil leader syringe",
    "three mil peter syringe",
    "get me five mill letter syringe",
    "10 mil leader please",
]

for command in test_commands:
    print(f"\nVoice Input: '{command}'")

    # Show normalization step
    normalized = normalize_abbreviations(command)
    print(f"Normalized: '{normalized}'")

    # Try matching
    result = matcher.match(normalized)
    if result:
        print(
            f"✓ MATCHED: {result['item']} (confidence: {result.get('confidence', 'N/A')})"
        )
    else:
        print("✗ No match found")

print("\n" + "=" * 70)
print("If all tests show ✓ MATCHED, the STT improvements are working!")
print("=" * 70 + "\n")
