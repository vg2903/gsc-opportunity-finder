
import streamlit as st
import pandas as pd
import traceback
import yaml
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime

# Import utility functions
from utils.query_analysis import detect_long_tail_queries, cluster_queries
from utils.gsc_api import match_queries_to_pages
from utils.content_suggestions import generate_h2s

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# -------------------------------
# Load configuration from config.yaml
# -------------------------------
try:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
except Exception:
    config = {}

# -------------------------------
# Streamlit App UI
# -------------------------------
st.set_page_config(page_title="GSC Opportunity Finder", layout="wide")
st.title("🔍 GSC Opportunity Finder")

# Sidebar Configuration Panel
st.sidebar.header("⚙️ App Settings")

min_words = st.sidebar.number_input("Min Words for Long-Tail Query", 1, 10, value=config.get("min_word_count", 3))
position_threshold = st.sidebar.number_input("Position Threshold", 1.0, 100.0, value=float(config.get("position_threshold", 20)))
use_clustering = st.sidebar.checkbox("Enable Query Clustering", value=config.get("use_clustering", True))

# API Keys
st.sidebar.header("🔑 API Keys (Optional)")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", value=config.get("openai_api_key", ""))
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=config.get("gemini_api_key", ""))

st.markdown("### 📥 Upload your GSC export and Buy Page list OR connect via Google OAuth")

# File uploaders
gsc_file = st.file_uploader("📈 Upload GSC CSV (with query, url, clicks, impressions, ctr, position)", type="csv")
buy_file = st.file_uploader("🛒 Upload Buy Page List CSV (with 'url' column)", type="csv")

# -------------------------------
# Google OAuth Integration
# -------------------------------
st.markdown("---")
st.markdown("### 🔐 Or connect directly to Google Search Console")

if "credentials" not in st.session_state:
    st.session_state.credentials = None

if not st.session_state.credentials:
    if os.path.exists("client_secret.json"):
        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=SCOPES,
            redirect_uri=st.experimental_get_url().split("/")[0]
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[👉 Connect your Google Account]({auth_url})")
    else:
        st.warning("client_secret.json not found for OAuth.")
else:
    credentials = st.session_state.credentials
    service = build("searchconsole", "v1", credentials=credentials)
    site_list = service.sites().list().execute()
    sites = [s["siteUrl"] for s in site_list["siteEntry"] if "siteUrl" in s]
    selected_site = st.selectbox("Select GSC Property", sites)

    if st.button("📡 Fetch GSC Data"):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=90)

        request = {
            "startDate": str(start),
            "endDate": str(today),
            "dimensions": ["query", "page"],
            "rowLimit": 5000
        }

        response = service.searchanalytics().query(siteUrl=selected_site, body=request).execute()
        rows = response.get("rows", [])
        data = []

        for row in rows:
            query = row["keys"][0]
            url = row["keys"][1]
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0)
            position = row.get("position", 0)
            data.append([query, url, clicks, impressions, ctr, position])

        gsc_df = pd.DataFrame(data, columns=["query", "url", "clicks", "impressions", "ctr", "position"])
        st.session_state["gsc_df"] = gsc_df
        st.success("✅ GSC Data fetched successfully.")
        st.dataframe(gsc_df.head())

# -------------------------------
# Main Logic
# -------------------------------
try:
    if (gsc_file or "gsc_df" in st.session_state) and buy_file:
        gsc_df = pd.read_csv(gsc_file) if gsc_file else st.session_state["gsc_df"]
        buy_df = pd.read_csv(buy_file)

        st.subheader("📊 GSC Data Preview")
        st.dataframe(gsc_df.head())

        st.subheader("📦 Buy Pages Preview")
        st.dataframe(buy_df.head())

        filtered_df = detect_long_tail_queries(gsc_df, min_word_count=min_words)
        filtered_df = filtered_df[filtered_df["position"] <= position_threshold]

        st.success(f"✅ {len(filtered_df)} queries passed filters.")
        st.dataframe(filtered_df.head())

        matched_df = match_queries_to_pages(filtered_df, buy_df)
        st.subheader("🧠 Opportunities (No matching page exists)")
        st.dataframe(matched_df.head())

        if use_clustering:
            st.info("🔄 Clustering queries...")
            clustered_df = cluster_queries(matched_df)
        else:
            clustered_df = matched_df
            clustered_df["cluster_id"] = 0

        if openai_key or gemini_key:
            st.info("🤖 Generating AI-based H2s...")
            clustered_df["suggested_h2s"] = clustered_df["query"].apply(
                lambda q: generate_h2s(q, openai_key=openai_key, gemini_key=gemini_key)
            )

        st.subheader("📤 Download Your Opportunity Report")
        csv = clustered_df.to_csv(index=False)
        st.download_button("⬇️ Download CSV", csv, "opportunity_report.csv", "text/csv")
    else:
        st.warning("👆 Upload both GSC and Buy Page files or connect via OAuth to continue.")
except Exception as e:
    st.error("❌ Something went wrong.")
    st.code(traceback.format_exc())
