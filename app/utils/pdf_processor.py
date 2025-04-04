from typing import List, Dict, Any, Optional, Union
from pypdf import PdfReader
import os
from pathlib import Path
import json
import pypdf
from pdf2image import convert_from_path
import pytesseract


class PDFProcessor:
    def __init__(self):
        self.data_dir = Path("data/legal_documents")
        self.temp_dir = Path("data/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def extract_text_from_pdf(
        self, pdf_path: str, structured: bool = False
    ) -> Union[str, List[Dict[str, Any]]]:
        """
        Extract text from a PDF file. If direct text extraction fails,
        falls back to OCR using pytesseract.

        Args:
            pdf_path: Path to the PDF file
            structured: If True, returns structured articles/sections
        """
        try:
            # First try direct text extraction
            text = self._extract_text_direct(pdf_path)

            # If no text was extracted, try OCR
            if not text.strip():
                text = self._extract_text_ocr(pdf_path)

            if structured:
                return self._structure_text(text)
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def _extract_text_direct(self, pdf_path: str) -> str:
        """Extract text directly from PDF using PyPDF."""
        try:
            text = []
            with open(pdf_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                print(f"PDF has {len(pdf_reader.pages)} pages")
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text.append(page_text)
                    if i < 2:  # Show first two pages for debugging
                        print(f"\nPage {i+1} sample (first 500 chars):")
                        print(page_text[:500])
            return "\n".join(text)
        except Exception as e:
            print(f"Warning: Direct text extraction failed: {str(e)}")
            return ""

    def _extract_text_ocr(self, pdf_path: str) -> str:
        """Extract text from PDF using OCR (Optical Character Recognition)."""
        try:
            # Convert PDF to images
            print("Converting PDF to images...")
            images = convert_from_path(pdf_path)
            print(f"Converted {len(images)} pages to images")

            # Extract text from each image using OCR
            text = []
            for i, image in enumerate(images):
                print(f"Processing page {i+1} with OCR...")
                # Save image temporarily
                image_path = self.temp_dir / f"page_{i}.png"
                image.save(str(image_path))

                # Extract text using pytesseract
                page_text = pytesseract.image_to_string(str(image_path))
                text.append(page_text)

                # Show sample of first two pages
                if i < 2:
                    print(f"\nPage {i+1} OCR sample (first 500 chars):")
                    print(page_text[:500])

                # Clean up temporary image
                os.remove(image_path)

            return "\n".join(text)
        except Exception as e:
            raise Exception(f"OCR text extraction failed: {str(e)}")

    def _structure_text(self, text: str) -> List[Dict[str, Any]]:
        """Structure the extracted text into articles/sections."""
        try:
            articles = []
            current_article = None
            current_content = []
            in_article_content = False

            print("Starting text structuring...")
            print(f"Total text length: {len(text)}")

            lines = text.split("\n")
            print(f"Total lines: {len(lines)}")

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                # More specific pattern for article headings
                is_article_heading = (
                    line.upper().startswith("ARTICLE ")
                    or line.upper().startswith("ART. ")
                    or (
                        line.upper().startswith("ARTICLE")
                        and any(c.isdigit() for c in line)
                    )
                )

                if is_article_heading:
                    print(f"Found article heading: {line}")
                    # Save previous article if exists
                    if current_article and current_content:
                        article_text = " ".join(current_content)
                        print(
                            f"Saving article {current_article} with length {len(article_text)}"
                        )
                        articles.append(
                            {
                                "number": current_article,
                                "content": article_text,
                            }
                        )
                        current_content = []

                    try:
                        # Extract article number - look for numbers after "ARTICLE" or "ART."
                        parts = line.upper().replace("ART.", "ARTICLE").split("ARTICLE")
                        if len(parts) > 1:
                            number_part = parts[1].strip()
                            # Extract the first number found
                            import re

                            numbers = re.findall(r"\d+", number_part)
                            if numbers:
                                current_article = numbers[0]
                                print(f"Extracted article number: {current_article}")
                            else:
                                current_article = f"section_{len(articles) + 1}"
                                print(f"No number found, using: {current_article}")
                        else:
                            current_article = f"section_{len(articles) + 1}"
                            print(f"No article number found, using: {current_article}")
                        in_article_content = True
                    except Exception as e:
                        print(
                            f"Error extracting article number from line '{line}': {str(e)}"
                        )
                        current_article = f"section_{len(articles) + 1}"
                        in_article_content = True
                else:
                    # Only append content if we're inside an article and the line doesn't contain "article" references
                    if current_article and in_article_content:
                        # Skip lines that are just article references
                        if not any(ref in line.lower() for ref in ["article", "art."]):
                            current_content.append(line)

            # Add the last article
            if current_article and current_content:
                article_text = " ".join(current_content)
                print(
                    f"Saving final article {current_article} with length {len(article_text)}"
                )
                articles.append({"number": current_article, "content": article_text})

            print(f"Structured {len(articles)} articles")
            if not articles:
                print("No articles found. First 1000 characters of text:")
                print(text[:1000])
            return articles
        except Exception as e:
            print(f"Error structuring text: {str(e)}")
            print(f"First 1000 characters of text: {text[:1000]}")
            return []

    def cleanup(self):
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.glob("*"):
                file.unlink()
        except Exception as e:
            print(f"Warning: Cleanup failed: {str(e)}")

    def process_constitution_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process the constitution PDF and return structured articles."""
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            print(f"Extracting text from {pdf_path}...")
            # Try direct extraction first
            text = self._extract_text_direct(pdf_path)
            print(f"Direct extraction result length: {len(text)}")

            if not text.strip():
                print("Direct extraction failed. Trying OCR...")
                text = self._extract_text_ocr(pdf_path)
                print(f"OCR result length: {len(text)}")

            if not text.strip():
                raise Exception("No text could be extracted from the PDF")

            print("Processing text into articles...")
            articles = self._structure_text(text)

            if articles:
                print(f"Saving {len(articles)} articles to JSON...")
                self.save_articles_to_json(articles, "constitution.json")
            else:
                print("No articles were found to save.")

            return articles
        except Exception as e:
            print(f"Error processing constitution PDF: {str(e)}")
            return []

    def save_articles_to_json(
        self, articles: List[Dict[str, Any]], output_file: str
    ) -> None:
        """Save extracted articles to a JSON file."""
        try:
            output_path = self.data_dir / output_file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"articles": articles}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving articles to JSON: {str(e)}")
