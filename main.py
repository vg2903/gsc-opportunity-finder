import streamlit as st
import pandas as pd
import traceback
import yaml
import tempfile
import json

# Import utility functions
from utils.query_analysis import detect_long_tail_queries, cluster_queries
from utils.gsc_api import match_queries_to_pages
from utils.content_suggestions import generate_h2s

# -------------------------------
# Load configuration
# -------------------------------
try:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
except Exception:
    config = {}

st.set_page_config(page_title="GSC Opportunity Finder", layout="wide")
st.title("🔍 GSC Opportunity Finder")
st.markdown("Connect to Google Search Console or upload CSV to discover long-tail content opportunities.")

# Sidebar Settings
st.sidebar.header("⚙️ App Settings")
min_words = st.sidebar.number_input("Min Words for Long-Tail Query", 1, 10, value=config.get("min_word_count", 3))
position_threshold = st.sidebar.number_input("Position Threshold", 1.0, 100.0, value=float(config.get("position_threshold", 20)))
use_clustering = st.sidebar.checkbox("Enable Query Clustering", value=config.get("use_clustering", True))

# API Keys
st.sidebar.header("🔑 API Keys (Optional)")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", value=config.get("openai_api_key", ""))
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=config.get("gemini_api_key", ""))

# Try to load Google OAuth
creds_dict = None
if "google_oauth" in st.secrets:
    creds_dict = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [st.secrets.get("redirect_uri", "https://your-app-name.streamlit.app")]
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
        json.dump(creds_dict, tmp)
        tmp_path = tmp.name

    st.success("✅ OAuth credentials found. (Login functionality coming soon...)")
else:
    st.info("Or connect directly to Google Search Console\n\n`client_secret.json` not found for OAuth.")

# Upload CSVs
st.header("📁 Upload GSC Data & Buy Page URLs")
gsc_file = st.file_uploader("📈 Upload GSC CSV (must have: query, url, clicks, impressions, ctr, position)", type="csv")
buy_file = st.file_uploader("🛒 Upload Buy Page List CSV (must have: url column)", type="csv")

try:
    if gsc_file and buy_file:
        gsc_df = pd.read_csv(gsc_file)
        buy_df = pd.read_csv(buy_file)

        st.subheader("📊 GSC Data Preview")
        st.dataframe(gsc_df.head())

        st.subheader("📦 Buy Pages Preview")
        st.dataframe(buy_df.head())

        # Step 1: Filter long-tail
        filtered_df = detect_long_tail_queries(gsc_df, min_word_count=min_words)
        filtered_df = filtered_df[filtered_df["position"] <= position_threshold]

        st.success(f"✅ {len(filtered_df)} queries passed long-tail and position filter.")
        st.dataframe(filtered_df.head())

        # Step 2: Match queries to buy pages
        matched_df = match_queries_to_pages(filtered_df, buy_df)
        st.subheader("🧠 Opportunities (No matching page exists)")
        st.dataframe(matched_df.head())

        # Step 3: Clustering
        if use_clustering:
            st.info("🔄 Clustering queries...")
            clustered_df = cluster_queries(matched_df)
        else:
            clustered_df = matched_df
            clustered_df["cluster_id"] = 0

        # Step 4: AI Suggestions (optional)
        if openai_key or gemini_key:
            st.info("🤖 Generating AI-based H2s...")
            clustered_df["suggested_h2s"] = clustered_df["query"].apply(
                lambda q: generate_h2s(q, openai_key=openai_key, gemini_key=gemini_key)
            )

        # Step 5: Export
        st.subheader("📤 Download Opportunity Report")
        csv = clustered_df.to_csv(index=False)
        st.download_button("⬇️ Download CSV", csv, "opportunity_report.csv", "text/csv")
    else:
        st.warning("👆 Upload both GSC and Buy Page CSVs to continue.")

except Exception as e:
    st.error("❌ Something went wrong.")
    st.code(traceback.format_exc())
