from functools import lru_cache
from nltk.sentiment.vader import SentimentIntensityAnalyzer

MODEL_NAME = "vader"


@lru_cache
def get_analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def score_text(text: str) -> dict[str, float]:
    analyzer = get_analyzer()
    return analyzer.polarity_scores(text)
