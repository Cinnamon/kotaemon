import requests

HF_API_URL = "https://huggingface.co/api/daily_papers"
ARXIV_URL = "https://arxiv.org/abs/{paper_id}"


def fetch_papers(top_n=5):
    try:
        response = requests.get(f"{HF_API_URL}?limit=100")
        response.raise_for_status()
        items = response.json()
        items.sort(key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True)
        items = [
            {
                "title": item.get("paper", {}).get("title"),
                "url": ARXIV_URL.format(paper_id=item.get("paper", {}).get("id")),
                "upvotes": item.get("paper", {}).get("upvotes"),
            }
            for item in items[:top_n]
        ]
    except Exception as e:
        print(e)
        return []

    return items
