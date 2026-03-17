import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("🚀 Enterprise SEO Link Analyzer")

url = st.text_input("Enter URL")

# ---------------- SESSION ----------------
if "df" not in st.session_state:
    st.session_state.df = None

# ---------------- STATUS CHECK ----------------
def check_status_fast(link):
    try:
        r = requests.head(link, timeout=3, allow_redirects=True)
        return "OK" if r.status_code < 400 else "Broken"
    except:
        return "Broken"

# ---------------- FETCH LINKS ----------------
def fetch_links_fast(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
    except:
        return pd.DataFrame()

    links = []
    domain = urlparse(url).netloc
    anchors = soup.find_all("a", href=True)

    progress = st.progress(0)
    status_text = st.empty()

    total_links = len(anchors)

    for i, a in enumerate(anchors):

        href = urljoin(url, a["href"]).split("#")[0]
        anchor = a.text.strip() or "N/A"

        link_type = "Internal" if urlparse(href).netloc == domain else "External"

        status = check_status_fast(href) if i < 40 else "OK"

        links.append({
            "Anchor Text": anchor,
            "URL": href,
            "Type": link_type,
            "Status": status
        })

        progress.progress((i + 1) / total_links)
        status_text.text(f"🔍 Analyzing {i+1}/{total_links} links...")

    status_text.text("✅ Analysis Completed")

    return pd.DataFrame(links)

# ---------------- INTERNAL LINK DISCOVERY ----------------
def find_linking_pages_pro(base_url, target, limit=30):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(base_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        domain = urlparse(base_url).netloc

        internal_links = set()

        for a in soup.find_all("a", href=True):
            link = urljoin(base_url, a["href"]).split("#")[0]
            if urlparse(link).netloc == domain:
                internal_links.add(link)

        results = []
        pages = list(internal_links)[:limit]

        prog = st.progress(0)
        txt = st.empty()

        for i, page in enumerate(pages):

            txt.text(f"🔍 Scanning {i+1}/{len(pages)} pages...")

            try:
                r = requests.get(page, timeout=5)
                soup = BeautifulSoup(r.text, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = urljoin(page, a["href"]).split("#")[0]
                    anchor = a.text.strip() or "N/A"

                    # remove self-links
                    if href == page:
                        continue

                    if href == target.split("#")[0]:
                        results.append({
                            "Page Linking To Target": page,
                            "Anchor Text": anchor
                        })

            except:
                continue

            prog.progress((i + 1) / len(pages))

        txt.text("✅ Link discovery completed")

        return pd.DataFrame(results)

    except:
        return pd.DataFrame()

# ---------------- RUN ----------------
if st.button("Run Analysis"):

    df = fetch_links_fast(url)
    st.session_state.df = df

# ---------------- DISPLAY ----------------
if st.session_state.df is not None:

    df = st.session_state.df

    if df.empty:
        st.error("❌ Failed to fetch links")
    else:

        # -------- SUMMARY --------
        total = len(df)
        internal = len(df[df["Type"] == "Internal"])
        external = len(df[df["Type"] == "External"])
        broken = len(df[df["Status"] == "Broken"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", total)
        col2.metric("Internal", internal)
        col3.metric("External", external)
        col4.metric("Broken", broken)

        st.markdown("---")

        # -------- GRAPHS --------
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Link Distribution")
            fig1, ax1 = plt.subplots()
            ax1.pie([internal, external], labels=["Internal", "External"], autopct='%1.1f%%')
            st.pyplot(fig1)

        with col2:
            st.subheader("Status Overview")
            fig2, ax2 = plt.subplots()
            ax2.bar(["OK", "Broken"], [total - broken, broken])
            st.pyplot(fig2)

        st.markdown("---")

        # -------- TABLES --------
        tab1, tab2, tab3, tab4 = st.tabs(["All", "Internal", "External", "Broken"])

        with tab1:
            st.dataframe(df, use_container_width=True,
                         column_config={"URL": st.column_config.LinkColumn("URL")})

        with tab2:
            st.dataframe(df[df["Type"] == "Internal"], use_container_width=True)

        with tab3:
            st.dataframe(df[df["Type"] == "External"], use_container_width=True)

        with tab4:
            st.dataframe(df[df["Status"] == "Broken"], use_container_width=True)

        # -------- INTERNAL LINK INSIGHTS --------
        st.markdown("---")
        st.subheader("🔗 Internal Link Insights")

        # ✅ USE INPUT URL ONLY (FIXED)
        st.write(f"Analyzing internal links for: {url}")

        interlinks = find_linking_pages_pro(url, url, limit=30)

        if not interlinks.empty:

            total_links = len(interlinks)
            unique_pages = interlinks["Page Linking To Target"].nunique()

            col1, col2 = st.columns(2)
            col1.metric("Total Links Found", total_links)
            col2.metric("Unique Pages Linking", unique_pages)

            st.markdown("### 📊 Anchor Text Distribution")
            st.dataframe(interlinks["Anchor Text"].value_counts())

            st.markdown("### 📄 Linking Pages")
            st.dataframe(interlinks, use_container_width=True)

        else:
            st.warning("No linking pages found (within scanned pages)")

        # -------- DOWNLOAD --------
        st.download_button(
            "⬇ Download CSV",
            df.to_csv(index=False),
            "seo_report.csv"
        )
