import fitz


def parse_pdf(file_path: str):

    doc = fitz.open(file_path)
    pages = []
    full_text = ""

    for page_num, page in enumerate(doc):
        text = page.get_text()
        full_text += text

        pages.append({
            "page": page_num + 1,
            "text": text
        })

    lines = full_text.splitlines()

    clean_lines = [
        line.strip()
        for line in lines
        if line.strip()
        and not line.startswith("Page")
    ]

    course_name = clean_lines[0]

    return {
        "course_name": course_name,
        "pages": pages
    }