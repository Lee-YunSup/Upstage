import requests, feedparser, datetime, smtplib, os, markdown
from email.message import EmailMessage
from requests.utils import quote
from langchain_upstage import UpstageDocumentParseLoader, ChatUpstage
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
load_dotenv()

EMAIL = os.getenv("EMAIL")
APP_PW = os.getenv("APP_PW")
UPSTAGE_KEY = os.getenv("UPSTAGE_API_KEY")

ARXIV_CATS = ["cs.CL", "cs.AI", "cs.LG"]
MAX_RESULTS = 50
MAX_SCAN = 500

def fetch_arxiv(start=0):
    cat_query = " OR ".join([f"cat:{c}" for c in ARXIV_CATS])
    encoded = quote(cat_query)
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={encoded}"
        f"&start={start}"
        f"&max_results={MAX_RESULTS}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    feed = feedparser.parse(url)
    return feed.entries

def is_top_venue(entry, venues):
    text = ""
    if hasattr(entry, "arxiv_comment"):
        text += entry.arxiv_comment.upper()
    if hasattr(entry, "journal_ref"):
        text += entry.journal_ref.upper()
    return any(v.upper() in text for v in venues)

def download_pdf(entry):
    pdf_url = [l.href for l in entry.links if l.type == "application/pdf"][0]
    title = entry.title.replace(" ", "_").replace("/", "_")[:60]
    filename = f"{title}.pdf"
    r = requests.get(pdf_url)
    with open(filename, "wb") as f:
        f.write(r.content)
    return filename

def parse_pdf(file_path):
    loader = UpstageDocumentParseLoader(file_path, ocr="auto", api_key=UPSTAGE_KEY)
    pages = loader.load()
    text = "\n".join([p.page_content for p in pages])
    if len(text.strip()) < 500:
        loader = UpstageDocumentParseLoader(file_path, ocr="force", api_key=UPSTAGE_KEY)
        pages = loader.load()
        text = "\n".join([p.page_content for p in pages])
    return text

def summarize(text):
    chat = ChatUpstage(api_key=UPSTAGE_KEY, model="solar-pro3", reasoning_effort="high")
    prompt = f"""
    다음은 AI 논문이다. 대학생이 빠르게 파악할 수 있도록 한국어로 정리하라.

    형식:
    - 한 줄 요약
    - 문제 정의
    - 핵심 아이디어
    - 방법 요약
    - 실험 결과 요지
    - 이 논문의 의미

    본문:
    {text[:12000]}
    """
    res = chat.invoke([HumanMessage(content=prompt)])
    return res.content

def send_email(to_addr, pdf_file, summary_md):
    html_body = markdown.markdown(summary_md, extensions=["tables"])

    msg = EmailMessage()
    msg["Subject"] = "[Paper Radar] 오늘의 논문 요약"
    msg["From"] = EMAIL
    msg["To"] = to_addr

    msg.set_content(summary_md)
    msg.add_alternative(
        f"<html><body style='font-family:Arial; line-height:1.6;'>{html_body}</body></html>",
        subtype="html",
    )

    with open(pdf_file, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=pdf_file,
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL, APP_PW)
        s.send_message(msg)

def run(to_email, venues):
    candidates = []
    start = 0

    while not candidates and start < MAX_SCAN:
        entries = fetch_arxiv(start=start)
        if not entries:
            break

        for e in entries:
            if is_top_venue(e, venues):
                published = datetime.datetime(*e.published_parsed[:6])
                candidates.append((e, published))

        start += MAX_RESULTS

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_entry, _ = candidates[0]

    file = download_pdf(best_entry)
    text = parse_pdf(file)
    summary = summarize(text)
    send_email(to_email, file, summary)

    return best_entry.title, best_entry.id
