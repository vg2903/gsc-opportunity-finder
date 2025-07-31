# utils/query_analysis.py

def detect_long_tail_queries(df, min_word_count=3):
    """
    Filters GSC query data for long-tail queries based on word count.
    """
    df = df.copy()
    df["word_count"] = df["query"].str.split().str.len()
    return df[df["word_count"] >= min_word_count]


def cluster_queries(df):
    """
    Dummy clustering logic for now — assigns all to cluster 0.
    Replace with cosine similarity or embedding-based clustering later.
    """
    df = df.copy()
    df["cluster_id"] = 0  # Placeholder cluster ID
    return df
