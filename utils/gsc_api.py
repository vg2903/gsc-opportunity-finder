# utils/gsc_api.py

def match_queries_to_pages(gsc_df, buy_df):
    """
    Matches long-tail queries with existing Buy page URLs.
    Flags queries where no matching Buy page exists.
    """
    gsc_df = gsc_df.copy()
    buy_urls = buy_df["url"].str.lower().tolist()

    def page_exists(query):
        return any(query.lower() in url for url in buy_urls)

    gsc_df["page_exists"] = gsc_df["query"].apply(page_exists)
    gsc_df["suggested_page"] = gsc_df["query"].str.replace(" ", "-", regex=False).str.lower()
    gsc_df["suggested_page"] = "/buy/" + gsc_df["suggested_page"]
    
    return gsc_df[gsc_df["page_exists"] == False]
