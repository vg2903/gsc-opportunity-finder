import streamlit as st
import pandas as pd
import traceback
import yaml
import tempfile
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from utils.query_analysis import detect_long_tail_queries, cluster_queries
from utils.gsc_api import match_queries_to_pages
from utils.content_suggestions import generate_h2s

# Load config
try:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
except:
    config = {}

st.set_page_config(page_title="GSC Opportunity Finder", layout="wide")
st.title("🔍 GSC Opportunity Finder")

st.sidebar.header("⚙️ App Settings")
min_words = st.sidebar.number_input("Min Words for Long-Tail Query", 1, 10, value=config.get("min_word_count", 3))
position_threshold = st.sidebar.number_input("Position Threshold", 1.0, 100.0, value=float(config.get("position_threshold", 20)))
use_clustering = st.sidebar.checkbox("Enable Query Clustering", value=config.get("use_clustering", True))
st.sidebar.header("🔑 API Keys (Optional)")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password", value=config.get("openai_api_key", ""))
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=config.get("gemini_api_key", ""))

# Load buy page file
buy_file = st.file_uploader("🛒 Upload Buy Page List CSV (must have 'url' column)", type="csv")

# GSC Auth Setup
creds_dict = None
if "google_oauth" in st.secrets:
    creds_dict = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets.get("redirect_uri", f"https://{st.secrets['custom_domain']}")],
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
        json.dump(creds_dict, tmp)
        client_secret_path = tmp.name
else:
    st.error("❌ Google OAuth credentials not found in secrets.toml.")
    st.stop()

# Step 1: Google OAuth Flow
if "credentials" not in st.session_state:
    auth_url, _ = Flow.from_client_secrets_file(
        client_secrets_file=client_secret_path,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        redirect_uri=creds_dict["web"]["redirect_uris"][0],
    ).authorization_url(prompt='consent')
    st.markdown(f"🔐 [Click here to log in with Google]({auth_url})")
    st.stop()

# Step 2: Use saved credentials
creds = Credentials.from_authorized_user_info(st.session_state["credentials"])
webmasters_service = build("searchconsole", "v1", credentials=creds)

# Step 3: Get user properties
site_list = webmasters_service.sites().list().execute()
verified_sites = [s["siteUrl"] for s in site_list["siteEntry"] if s["permissionLevel"] != "siteUnverifiedUser"]
selected_property = st.selectbox("📍 Select GSC Property", options=verified_sites)

# Step 4: Pull GSC query data
if selected_property and buy_file:
    st.info("📥 Fetching GSC data...")
    response = webmasters_service.searchanalytics().query(
        siteUrl=selected_property,
        body={
            "startDate": "2024-06-01",
            "endDate": "2024-07-31",
            "dimensions": ["query", "page"],
            "rowLimit": 50000
        }
    ).execute()

    rows = response.get("rows", [])
    gsc_data = [{"query": r["keys"][0], "url": r["keys"][1], "clicks": r["clicks"],
                 "impressions": r["impressions"], "ctr": r["ctr"], "position": r["position"]}
                for r in rows]
    gsc_df = pd.DataFrame(gsc_data)
    st.success(f"✅ Pulled {len(gsc_df)} rows from GSC.")
    st.dataframe(gsc_df.head())

    buy_df = pd.read_csv(buy_file)
    st.subheader("📦 Buy Pages Preview")
    st.dataframe(buy_df.head())

    # Long-tail filtering
    filtered_df = detect_long_tail_queries(gsc_df, min_word_count=min_words)
    filtered_df = filtered_df[filtered_df["position"] <= position_threshold]
    st.success(f"✅ {len(filtered_df)} queries passed long-tail and position filter.")

    # Match to Buy Pages
    matched_df = match_queries_to_pages(filtered_df, buy_df)
    st.subheader("🧠 Opportunities (No matching page exists)")
    st.dataframe(matched_df.head())

    # Clustering
    if use_clustering:
        clustered_df = cluster_queries(matched_df)
    else:
        clustered_df = matched_df
        clustered_df["cluster_id"] = 0

    # AI H2s
    if openai_key or gemini_key:
        st.info("🤖 Generating AI-based H2s...")
        clustered_df["suggested_h2s"] = clustered_df["query"].apply(
            lambda q: generate_h2s(q, openai_key=openai_key, gemini_key=gemini_key)
        )

    st.subheader("📤 Download Opportunity Report")
    csv = clustered_df.to_csv(index=False)
    st.download_button("⬇️ Download CSV", csv, "opportunity_report.csv", "text/csv")

elif not buy_file:
    st.warning("Please upload the Buy Page URL list to continue.")
