#!/usr/bin/env python3
"""
Iterative OCR Training Script for Virtual Mailroom
Trains on specific file number patterns: 1L+7N, 2L+6N, or 8N
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pdfplumber
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IterativeOCRTrainer:
    """Iterative training for file number pattern recognition"""

    def __init__(self):
        # Core file number patterns based on actual format rules
        # 1 letter + 7 numbers (e.g., L2401724, Y1301388)
        # 2 letters + 6 numbers (e.g., JM221025, EF202514)
        # 8 numbers (e.g., 12345678)
        self.pattern_rules = [
            (r'^[A-Z]\d{7}$', '1L+7N'),
            (r'^[A-Z]{2}\d{6}$', '2L+6N'),
            (r'^\d{8}$', '8N'),
        ]

        # Initialize pattern variations for finding candidates
        self.search_patterns = []
        self.failed_extractions = []
        self.successful_patterns = []
        self.pattern_scores = Counter()

        # Training data
        self.training_rounds = []
        self.current_round = 0

    def validate_file_number(self, candidate: str) -> Tuple[bool, str]:
        """Validate if candidate matches expected format"""
        candidate = candidate.strip().upper()
        candidate = re.sub(r'[^A-Z0-9]', '', candidate)

        for pattern, format_type in self.pattern_rules:
            if re.match(pattern, candidate):
                return True, format_type

        return False, None

    def generate_search_patterns(self, round_num: int) -> List[str]:
        """Generate increasingly sophisticated search patterns for each round"""

        patterns = []

        if round_num == 1:
            # Round 1: Basic patterns
            patterns = [
                r'File\s*No[.:]\s*([A-Z]{1,2}\d{6,7})',
                r'File\s*Number[:\s]*([A-Z]{1,2}\d{6,7})',
                r'Our\s*File[:\s]*([A-Z]{1,2}\d{6,7})',
                r'Account\s*#?[:\s]*([A-Z]{1,2}\d{6,7})',
                r'File\s*No[.:]\s*(\d{8})',
            ]

        elif round_num == 2:
            # Round 2: Handle OCR spacing issues
            patterns = [
                r'File\s*No[.:]\s*([A-Z]\s*\d{7})',  # Space between letter and numbers
                r'File\s*No[.:]\s*([A-Z]{2}\s*\d{6})',
                r'F\s*i\s*l\s*e\s*N\s*o[.:]\s*([A-Z]{1,2}\d{6,7})',  # Spaced out letters
                r'Account\s*(?:Number|#)[:\s]*([A-Z]{1,2}\s*\d{6,7})',
                r'Reference[:\s]*([A-Z]{1,2}\d{6,7})',
            ]

        elif round_num == 3:
            # Round 3: OCR error corrections (O/0, I/1, etc.)
            patterns = [
                r'File\s*N[o0][.:]\s*([A-Z0-9]{7,8})',  # O vs 0
                r'F[i1]le\s*No[.:]\s*([A-Z0-9]{7,8})',  # I vs 1
                r'File\s*No[.:]\s*([A-Z0-9]\s*[0-9]{6,7})',
                r'Acct\.?\s*#?\s*([A-Z]{0,2}[0-9]{6,8})',
                r'Matter\s*#?\s*([A-Z]{0,2}[0-9]{6,8})',
            ]

        elif round_num == 4:
            # Round 4: Learn from failures - look anywhere in text
            patterns = [
                r'([A-Z]\d{7})\b',  # Any 1L+7N pattern
                r'([A-Z]{2}\d{6})\b',  # Any 2L+6N pattern
                r'\b(\d{8})\b',  # Any 8N pattern
                r'([A-Z][0-9\s]{7,9})',  # Letter followed by numbers with possible spaces
                r'([A-Z]{2}[0-9\s]{6,8})',  # Two letters followed by numbers
            ]

        elif round_num == 5:
            # Round 5: Aggressive extraction with validation
            patterns = [
                # Look for patterns near keywords
                r'(?:File|Account|Reference|Matter|Our|Acct)[^\n]{0,20}([A-Z]{1,2}[\d\s]{6,8})',
                # Look for patterns after colons
                r':\s*([A-Z]{1,2}[\d\s]{6,8})',
                # Look for patterns in parentheses
                r'\(([A-Z]{1,2}\d{6,7})\)',
                # Any valid pattern anywhere
                r'([A-Z]\d{7}|[A-Z]{2}\d{6}|\d{8})',
            ]

        # Add successful patterns from previous rounds
        patterns.extend(self.successful_patterns)

        return patterns

    def extract_candidates(self, text: str, patterns: List[str]) -> List[Tuple[str, str]]:
        """Extract potential file numbers using patterns"""
        candidates = []

        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]

                    # Clean the match
                    cleaned = match.strip().upper()
                    cleaned = re.sub(r'\s+', '', cleaned)  # Remove internal spaces

                    # Validate format
                    is_valid, format_type = self.validate_file_number(cleaned)
                    if is_valid:
                        candidates.append((cleaned, format_type))
                        self.pattern_scores[pattern] += 1

            except Exception as e:
                logger.debug(f"Pattern error: {pattern} - {e}")

        return candidates

    def run_training_round(self, test_files: List[Path], round_num: int) -> Dict:
        """Run a single training round"""

        logger.info(f"\n{'='*60}")
        logger.info(f"TRAINING ROUND {round_num}")
        logger.info(f"{'='*60}")

        # Generate patterns for this round
        patterns = self.generate_search_patterns(round_num)
        logger.info(f"Testing {len(patterns)} patterns")

        round_results = {
            "round": round_num,
            "patterns_tested": len(patterns),
            "files": {},
            "success_count": 0,
            "total_files": 0,
        }

        # Test each file
        for pdf_file in test_files:
            filename = pdf_file.name
            round_results["total_files"] += 1

            try:
                # Extract text
                with pdfplumber.open(pdf_file) as pdf:
                    all_text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        all_text += page_text + "\n"

                # Extract candidates
                candidates = self.extract_candidates(all_text, patterns)

                if candidates:
                    # Take the first valid candidate
                    found_number = candidates[0][0]
                    format_type = candidates[0][1]

                    round_results["files"][filename] = {
                        "found": found_number,
                        "format": format_type,
                        "candidates": candidates[:3],  # Top 3 candidates
                    }
                    round_results["success_count"] += 1

                    logger.info(f"  ✅ {filename}: Found {found_number} ({format_type})")

                    # Remember successful patterns
                    for pattern in patterns:
                        if re.search(pattern, all_text, re.IGNORECASE):
                            if pattern not in self.successful_patterns:
                                self.successful_patterns.append(pattern)
                else:
                    round_results["files"][filename] = {
                        "found": None,
                        "format": None,
                        "candidates": [],
                    }
                    self.failed_extractions.append((filename, all_text[:500]))
                    logger.info(f"  ❌ {filename}: No valid file number found")

            except Exception as e:
                logger.error(f"  ⚠️  {filename}: Error - {e}")
                round_results["files"][filename] = {"error": str(e)}

        # Calculate success rate
        success_rate = (round_results["success_count"] / round_results["total_files"]) * 100 if round_results["total_files"] > 0 else 0
        round_results["success_rate"] = success_rate

        logger.info(f"\nRound {round_num} Results: {round_results['success_count']}/{round_results['total_files']} ({success_rate:.1f}%)")

        return round_results

    def analyze_failures(self) -> List[str]:
        """Analyze failed extractions to suggest new patterns"""
        suggestions = []

        for filename, text_sample in self.failed_extractions[-5:]:  # Last 5 failures
            logger.debug(f"Analyzing failure: {filename}")

            # Look for potential patterns
            potential_patterns = re.findall(r'[A-Z]{1,2}\d{6,7}|\d{8}', text_sample)
            if potential_patterns:
                suggestions.append(f"Consider pattern near: {potential_patterns[0]}")

        return suggestions

    def run_iterative_training(self, test_dir: str, num_rounds: int = 5):
        """Run iterative training rounds"""

        test_dir_path = Path(test_dir)
        test_files = list(test_dir_path.glob("*.pdf")) + list(test_dir_path.glob("*.PDF"))

        if not test_files:
            logger.error(f"No PDF files found in {test_dir}")
            return

        logger.info(f"Starting iterative training with {len(test_files)} files")
        logger.info(f"Expected formats: 1L+7N, 2L+6N, or 8N only")

        # Run training rounds
        for round_num in range(1, num_rounds + 1):
            round_results = self.run_training_round(test_files, round_num)
            self.training_rounds.append(round_results)

            # Early stopping if we achieve 100% success
            if round_results["success_rate"] == 100:
                logger.info(f"🎯 Achieved 100% success in round {round_num}!")
                break

            # Analyze failures after each round
            if round_num < num_rounds and round_results["success_rate"] < 100:
                suggestions = self.analyze_failures()
                if suggestions:
                    logger.info("Learning from failures...")
                    for suggestion in suggestions:
                        logger.debug(f"  - {suggestion}")

        # Final summary
        self.print_final_summary()

    def print_final_summary(self):
        """Print comprehensive training summary"""

        logger.info(f"\n{'='*60}")
        logger.info("ITERATIVE TRAINING SUMMARY")
        logger.info(f"{'='*60}")

        # Success progression
        logger.info("\nSuccess Rate by Round:")
        for round_data in self.training_rounds:
            logger.info(f"  Round {round_data['round']}: {round_data['success_rate']:.1f}%")

        # Best performing patterns
        logger.info("\nTop Performing Patterns:")
        for pattern, count in self.pattern_scores.most_common(5):
            logger.info(f"  {count} matches: {pattern[:60]}...")

        # Final recommendations
        best_round = max(self.training_rounds, key=lambda x: x['success_rate'])
        logger.info(f"\nBest Round: {best_round['round']} with {best_round['success_rate']:.1f}% success")

        # Save results
        output_file = f"iterative_training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "rounds": self.training_rounds,
                "successful_patterns": self.successful_patterns,
                "pattern_scores": dict(self.pattern_scores),
            }, f, indent=2)
        logger.info(f"\nDetailed results saved to {output_file}")

        # Generate optimized pattern list
        self.generate_optimized_patterns()

    def generate_optimized_patterns(self):
        """Generate optimized pattern list based on training"""

        logger.info("\n" + "="*60)
        logger.info("OPTIMIZED PATTERN RECOMMENDATIONS")
        logger.info("="*60)

        optimized = []

        # Add top performing patterns
        for pattern, _ in self.pattern_scores.most_common(10):
            if pattern not in optimized:
                optimized.append(pattern)

        logger.info("\nRecommended pattern order for pdf_splitter.py:")
        for i, pattern in enumerate(optimized[:7], 1):
            logger.info(f"  {i}. r'{pattern}'")

        # Save to file
        with open("optimized_file_patterns.py", 'w') as f:
            f.write("# Optimized file number patterns from iterative training\n")
            f.write("FILE_NUMBER_PATTERNS = [\n")
            for pattern in optimized[:7]:
                f.write(f"    r'{pattern}',\n")
            f.write("]\n")
        logger.info("\nOptimized patterns saved to optimized_file_patterns.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Iterative OCR training for file number extraction')
    parser.add_argument('test_dir', help='Directory containing test PDFs')
    parser.add_argument('--rounds', type=int, default=5, help='Number of training rounds (default: 5)')

    args = parser.parse_args()

    trainer = IterativeOCRTrainer()
    trainer.run_iterative_training(args.test_dir, args.rounds)


if __name__ == "__main__":
    main()