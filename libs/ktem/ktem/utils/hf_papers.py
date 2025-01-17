from datetime import datetime, timedelta

import requests
from cachetools import TTLCache, cached

HF_API_URL = "https://huggingface.co/api/daily_papers"
ARXIV_URL = "https://arxiv.org/abs/{paper_id}"
SEMANTIC_SCHOLAR_QUERY_URL = "https://api.semanticscholar.org/graph/v1/paper/search/match?query={paper_name}"  # noqa
SEMANTIC_SCHOLAR_RECOMMEND_URL = (
    "https://api.semanticscholar.org/recommendations/v1/papers/"  # noqa
)
CACHE_TIME = 60 * 60 * 6  # 6 hours


# Function to parse the date string
def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")


@cached(cache=TTLCache(maxsize=500, ttl=CACHE_TIME))
def get_recommendations_from_semantic_scholar(semantic_scholar_id: str):
    try:
        r = requests.post(
            SEMANTIC_SCHOLAR_RECOMMEND_URL,
            json={
                "positivePaperIds": [semantic_scholar_id],
            },
            params={"fields": "externalIds,title,year", "limit": 14},  # type: ignore
        )
        return r.json()["recommendedPapers"]
    except KeyError as e:
        print(e)
        return []


def filter_recommendations(recommendations, max_paper_count=5):
    # include only arxiv papers
    arxiv_paper = [
        r for r in recommendations if r["externalIds"].get("ArXiv", None) is not None
    ]
    if len(arxiv_paper) > max_paper_count:
        arxiv_paper = arxiv_paper[:max_paper_count]
    return arxiv_paper


def format_recommendation_into_markdown(recommendations):
    comment = "(recommended by the Semantic Scholar API)\n\n"
    for r in recommendations:
        hub_paper_url = f"https://arxiv.org/abs/{r['externalIds']['ArXiv']}"
        comment += f"* [{r['title']}]({hub_paper_url}) ({r['year']})\n"

    return comment


def get_paper_id_from_name(paper_name):
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_QUERY_URL.format(paper_name=paper_name)
        )
        response.raise_for_status()
        items = response.json()
        paper_id = items.get("data", [])[0].get("paperId")
    except Exception as e:
        print(e)
        return None

    return paper_id


def get_recommended_papers(paper_name):
    paper_id = get_paper_id_from_name(paper_name)
    recommended_content = ""
    if paper_id is None:
        return recommended_content

    recommended_papers = get_recommendations_from_semantic_scholar(paper_id)
    filtered_recommendations = filter_recommendations(recommended_papers)

    recommended_content = format_recommendation_into_markdown(filtered_recommendations)
    return recommended_content


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
