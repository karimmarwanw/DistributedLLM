import argparse
from pathlib import Path
import subprocess

import requests

from rag.vector_store import upsert_document


def extract_pdf_text(file_path):
    try:
        result = subprocess.run(
            ["pdftotext", file_path, "-"],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except FileNotFoundError as error:
        raise RuntimeError("pdftotext is required to ingest PDF files.") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or "Unable to extract text from PDF."
        raise RuntimeError(message) from error


def read_document_text(args):
    if args.text:
        return args.text

    if args.file:
        file_path = Path(args.file)

        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        if file_path.suffix.lower() == ".pdf":
            return extract_pdf_text(str(file_path))

        with open(file_path, "r", encoding="utf-8") as document_file:
            return document_file.read()

    raise ValueError("Provide either --text or --file.")


def ingest_via_api(args, text):
    response = requests.post(
        f"{args.rag_url.rstrip('/')}/documents",
        json={
            "source": args.source,
            "text": text,
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap
        },
        timeout=args.timeout
    )
    response.raise_for_status()
    return response.json()


def ingest_direct(args, text):
    return {
        "success": True,
        **upsert_document(
            source=args.source,
            text=text,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap
        )
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--text")
    parser.add_argument("--file")
    parser.add_argument("--rag-url")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--chunk-size", type=int, default=700)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    args = parser.parse_args()

    text = read_document_text(args)

    if args.rag_url:
        result = ingest_via_api(args, text)
    else:
        result = ingest_direct(args, text)

    print(result)


if __name__ == "__main__":
    main()
