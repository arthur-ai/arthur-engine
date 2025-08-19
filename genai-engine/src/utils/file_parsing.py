import csv
import logging
import re
from io import BytesIO, TextIOWrapper

from pypdf import PdfReader
from arthur_common.models.enums import DocumentType
from schemas.internal_schemas import Document

logger = logging.getLogger()


def parse_file_words(document: Document, file_content: BytesIO):
    if document.type == DocumentType.CSV:
        return parse_csv(file_content)
    elif document.type == DocumentType.PDF:
        return parse_pdf(file_content)
    elif document.type == DocumentType.TXT:
        return parse_txt(file_content)
    else:
        raise NotImplementedError("File upload for %s is not supported" % document.name)


def parse_pdf(pdf_file):
    words = []
    try:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text = page.extract_text()
            page_words = re.findall(r"\b\w+\b", text)
            words.extend(page_words)
    except Exception as e:
        logger.error(f"Failed to extract words from PDF: {e}")
        raise e
    return words


def parse_csv(csv_file):
    words = []
    try:
        csv_text = TextIOWrapper(csv_file, encoding="utf-8")
        reader = csv.reader(csv_text)

        for row in reader:
            for item in row:
                item_words = re.findall(r"\b\w+\b", item)
                words.extend(item_words)
    except Exception as e:
        logger.error(f"Failed to extract words from CSV: {e}")
        raise e
    return words


def parse_txt(txt_file: BytesIO):
    words = []
    try:
        text = txt_file.read().decode(encoding="utf-8")
        page_words = re.findall(r"\b\w+\b", text)
        words.extend(page_words)
    except Exception as e:
        logger.error(f"Failed to extract words from text file: {e}")
        raise e
    return words
