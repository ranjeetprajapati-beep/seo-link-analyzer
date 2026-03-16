import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import tldextract
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="SEO Link Analyzer", layout="wide")

# Browser headers (fix false broken links)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

session = requests.Session()
session.headers.update(headers)

# -----------------------------
# Custom UI Styling
# -----------------------------
st.markdown("""
<style>

body {
background-color:#f4f7fc;
}

.title {
font-size:40px;
font-weight:800;
color:#1f4e79;
}

.metric-card {
background: linear-gradient(135deg,#4facfe,#00f2fe);
padding:20px;
border-radius:12px;
text-align:center;
color:white;
box-shadow:0 6px 15px rgba(0,0,0,0.2);
}

.metric-number{
font-size:32px;
font-weight:700;
}

</style>
""", unsafe_allow_html=True)


# -----------------------------
# Link Status Checker
# -----------------------------
def check_status(url):

    try:

        r = session.get(url, allow_redirects=True, timeout=10)

        status = r.status_code

        if status == 404:
            return "Broken"

        elif status in [301,302]:
            return "Redirect"

        elif status >= 500:
            return "Server Error"

        elif status == 403:
            return "Blocked"

        else:
            return "OK"

    except:
        return "Broken"


# -----------------------------
# Analyze Page
# -----------------------------
def analyze_page(url):

    r = session.get(url)

    soup = BeautifulSoup(r.text,"html.parser")

    links = soup.find_all("a",href=True)

    data=[]

    domain = tldextract.extract(url).registered_domain

    urls=[]
    anchors=[]
    types=[]

    for a in links:

        href = a["href"]
        anchor = a.get_text(strip=True)

        full_url = urljoin(url,href)

        link_domain = tldextract.extract(full_url).registered_domain

        link_type = "Internal" if domain == link_domain else "External"

        urls.append(full_url)
        anchors.append(anchor)
        types.append(link_type)

    # Faster link checking
    with ThreadPoolExecutor(max_workers=15) as executor:
        statuses=list(executor.map(check_status,urls))

    for i in range(len(urls)):

        data.append({

            "Anchor Text":anchors[i],
            "URL":urls[i],
            "Type":types[i],
            "Status":statuses[i]

        })

    df=pd.DataFrame(data)

    return df


# -----------------------------
# Crawl Website
# -----------------------------
def crawl_site(start_url,max_pages=20):

    visited=set()
    to_visit=[start_url]

    domain=urlparse(start_url).netloc

    pages=[]

    while to_visit and len(visited)<max_pages:

        url=to_visit.pop(0)

        if url in visited:
            continue

        visited.add(url)
        pages.append(url)

        try:

            r=session.get(url)

            soup=BeautifulSoup(r.text,"html.parser")

            for a in soup.find_all("a",href=True):

                link=urljoin(url,a["href"])

                if domain in urlparse(link).netloc and link not in visited:

                    to_visit.append(link)

        except:
            continue

    return pages


# -----------------------------
# Find Interlinks
# -----------------------------
def find_interlinks(target_url,pages):

    results=[]

    for page in pages:

        try:

            r=session.get(page)

            soup=BeautifulSoup(r.text,"html.parser")

            for a in soup.find_all("a",href=True):

                link=urljoin(page,a["href"])

                if link==target_url:

                    results.append({

                        "Page Linking To Target":page,
                        "Anchor Text":a.get_text(strip=True)

                    })

        except:
            continue

    return pd.DataFrame(results)


# -----------------------------
# UI
# -----------------------------
st.markdown('<p class="title">🚀 SEO Link Analyzer + Internal Link Finder</p>', unsafe_allow_html=True)

url = st.text_input("Enter Page URL")


if st.button("Analyze Page"):

    st.session_state.df = analyze_page(url)

if "df" in st.session_state:

    df = st.session_state.df

    total_links = len(df)
    internal_links = len(df[df["Type"]=="Internal"])
    external_links = len(df[df["Type"]=="External"])
    broken_links = len(df[df["Status"]=="Broken"])
    redirects = len(df[df["Status"]=="Redirect"])


    st.subheader("Summary")

    col1,col2,col3,col4,col5 = st.columns(5)

    col1.markdown(f"<div class='metric-card'>Total Links<br><span class='metric-number'>{total_links}</span></div>", unsafe_allow_html=True)

    col2.markdown(f"<div class='metric-card'>Internal Links<br><span class='metric-number'>{internal_links}</span></div>", unsafe_allow_html=True)

    col3.markdown(f"<div class='metric-card'>External Links<br><span class='metric-number'>{external_links}</span></div>", unsafe_allow_html=True)

    col4.markdown(f"<div class='metric-card'>Broken Links<br><span class='metric-number'>{broken_links}</span></div>", unsafe_allow_html=True)

    col5.markdown(f"<div class='metric-card'>Redirects<br><span class='metric-number'>{redirects}</span></div>", unsafe_allow_html=True)


    # -----------------------------
    # Chart
    # -----------------------------
    chart_data=pd.DataFrame({

        "Type":["Internal","External","Broken","Redirect"],
        "Count":[internal_links,external_links,broken_links,redirects]

    })

    st.subheader("Link Distribution")

    st.bar_chart(chart_data.set_index("Type"))


    # -----------------------------
    # Filter Links
    # -----------------------------
    option=st.selectbox(

        "Filter Links",

        [
            "All Links",
            "Internal Links",
            "External Links",
            "Broken Links",
            "Redirects"
        ]

    )

    filtered=df

    if option=="Internal Links":
        filtered=df[df["Type"]=="Internal"]

    elif option=="External Links":
        filtered=df[df["Type"]=="External"]

    elif option=="Broken Links":
        filtered=df[df["Status"]=="Broken"]

    elif option=="Redirects":
        filtered=df[df["Status"]=="Redirect"]


    st.subheader("Link Report")

    st.dataframe(filtered, use_container_width=True)


    # -----------------------------
    # CSV Download
    # -----------------------------
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download CSV",
        csv,
        "link_report.csv",
        "text/csv"
    )


    # -----------------------------
    # Interlink Finder
    # -----------------------------
    st.subheader("Find Pages Linking To This URL")

    with st.spinner("Searching internal links..."):

        pages=crawl_site(url)

        interlinks=find_interlinks(url,pages)

    if not interlinks.empty:

        st.dataframe(interlinks, use_container_width=True)

        st.download_button(

            "Download Interlink Report",

            interlinks.to_csv(index=False),

            "interlink_report.csv"

        )

    else:

        st.info("No pages found linking to this URL.")