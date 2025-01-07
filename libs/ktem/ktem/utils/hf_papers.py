from datetime import datetime, timedelta

import requests

HF_API_URL = "https://huggingface.co/api/daily_papers"
ARXIV_URL = "https://arxiv.org/abs/{paper_id}"


# Function to parse the date string
def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def fetch_papers(top_n=5):
    try:
        response = requests.get(f"{HF_API_URL}?limit=100")
        response.raise_for_status()
        items = response.json()

        # Calculate the date 3 days ago from now
        three_days_ago = datetime.now() - timedelta(days=3)

        # Filter items from the last 3 days
        recent_items = [
            item
            for item in items
            if parse_date(item.get("publishedAt")) >= three_days_ago
        ]

        recent_items.sort(
            key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True
        )
        output_items = [
            {
                "title": item.get("paper", {}).get("title"),
                "url": ARXIV_URL.format(paper_id=item.get("paper", {}).get("id")),
                "upvotes": item.get("paper", {}).get("upvotes"),
            }
            for item in recent_items[:top_n]
        ]
    except Exception as e:
        print(e)
        return []

    return output_items
