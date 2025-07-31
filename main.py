import streamlit as st
import pandas as pd
import traceback
from utils.query_analysis import detect_long_tail_queries, cluster_queries
from utils.content_suggestions import generate_h2s
from utils.gsc_api import match_queries_to_pages

# App Title
st.set_page_config(page_title="GSC Opportunity Finder", layout="wide")
st.title("🔍 GSC Opportunity Finder")
st.markdown("Upload your GSC query data and Buy Page list to find missed long-tail keyword opportunities.")

try:
    # Upload GSC CSV
    gsc_file = st.file_uploader("📈 Upload Google Search Console (GSC) CSV", type=["csv"])
    
    # Upload Buy Page List
    buy_file = st.file_uploader("🛒 Upload Buy Page URLs (CSV)", type=["csv"])

    # API Key Inputs (Optional)
    st.sidebar.header("🔑 API Configuration")
    openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password")

    # Configuration
    min_words = st.sidebar.slider("Min Words for Long-Tail Query", 2, 6, 3)
    use_clustering = st.sidebar.checkbox("Enable Query Clustering", value=True)

    if gsc_file and buy_file:
        # Read files
        gsc_df = pd.read_csv(gsc_file)
        buy_df = pd.read_csv(buy_file)

        # Preview
        st.subheader("📊 Preview: GSC Data")
        st.dataframe(gsc_df.head())

        st.subheader("📦 Preview: Buy Page URLs")
        st.dataframe(buy_df.head())

        # Step 1: Detect long-tail queries
        long_tail_df = detect_long_tail_queries(gsc_df, min_word_count=min_words)
        st.success(f"✅ Found {len(long_tail_df)} long-tail queries.")
        st.dataframe(long_tail_df.head())

        # Step 2: Match to existing Buy Pages
        matched_df = match_queries_to_pages(long_tail_df, buy_df)
        st.subheader("🧠 Potential Opportunities (Unmatched Queries)")
        st.dataframe(matched_df.head())

        # Step 3: Optional clustering
        if use_clustering:
            st.info("Clustering queries...")
            clustered_df = cluster_queries(matched_df)
            st.dataframe(clustered_df.head())
        else:
            clustered_df = matched_df

        # Step 4: Optional H2 Suggestions via GPT
        if openai_key or gemini_key:
            st.info("Generating H2s for top queries using AI...")
            clustered_df["suggested_h2s"] = clustered_df["query"].apply(
                lambda q: generate_h2s(q, openai_key=openai_key, gemini_key=gemini_key)
            )
            st.dataframe(clustered_df[["query", "suggested_h2s"]].head())

        # Export
        st.download_button("⬇️ Download CSV", clustered_df.to_csv(index=False), file_name="gsc_opportunity_report.csv", mime="text/csv")

    else:
        st.warning("👆 Please upload both GSC data and Buy Page list to begin.")

except Exception as e:
    st.error("❌ An error occurred while processing your request.")
    st.code(traceback.format_exc())
