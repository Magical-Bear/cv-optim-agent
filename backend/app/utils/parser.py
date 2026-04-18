from io import BytesIO


def parse_file(data: bytes, ext: str) -> str:
    if ext == "pdf":
        return _parse_pdf(data)
    elif ext == "docx":
        return _parse_docx(data)
    raise ValueError(f"Unsupported extension: {ext}")


def _parse_pdf(data: bytes) -> str:
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)

    if not text_parts:
        raise ValueError("No extractable text found. Scanned PDF — please paste text instead.")

    return "\n".join(text_parts)


def _parse_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise ValueError("Empty Word document.")
    return "\n".join(paragraphs)
