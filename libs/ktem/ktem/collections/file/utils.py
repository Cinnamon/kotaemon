import os

import requests

# regex patterns for Arxiv URL
ARXIV_URL_PATTERNS = [
    "https://arxiv.org/abs/",
    "https://arxiv.org/pdf/",
]

ILLEGAL_NAME_CHARS = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]


def clean_name(name):
    for char in ILLEGAL_NAME_CHARS:
        name = name.replace(char, "_")
    return name


def is_arxiv_url(url):
    return any(url.startswith(pattern) for pattern in ARXIV_URL_PATTERNS)


# download PDF from Arxiv URL
def download_arxiv_pdf(url, output_path):
    if not is_arxiv_url(url):
        raise ValueError("Invalid Arxiv URL")

    is_abstract_url = "abs" in url
    if is_abstract_url:
        pdf_url = url.replace("abs", "pdf")
        abstract_url = url
    else:
        pdf_url = url
        abstract_url = url.replace("pdf", "abs")

    # get paper name from abstract url
    response = requests.get(abstract_url)

    # parse HTML response and get h1.title
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.content, "html.parser")
    name = clean_name(
        soup.find("h1", class_="title").text.strip().replace("Title:", "")
    )
    if not name:
        raise ValueError("Failed to get paper name")

    output_file_path = os.path.join(output_path, name + ".pdf")
    # prevent downloading if file already exists
    if not os.path.exists(output_file_path):
        response = requests.get(pdf_url)

        with open(output_file_path, "wb") as f:
            f.write(response.content)

    return output_file_path
