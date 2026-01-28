import streamlit as st
import json, os
from agent import run
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"

st.set_page_config(page_title="Paper Radar", page_icon="📡", layout="centered")

default_email = ""
default_venues = ""
default_time = "08:00"

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        default_email = cfg.get("email", "")
        default_venues = "\n".join(cfg.get("venues", []))
        default_time = cfg.get("time", "08:00")

st.title("하루 한 편, 3분 논문📑")
st.caption("논문을 습관으로 만드는 가장 쉬운 방법")

with st.sidebar:
    st.header("구독 설정")

    to_email = st.text_input("이메일", value=default_email)

    st.markdown("<hr style='margin: 0.7rem 0; border: none; border-top: 1px solid #ddd;' />", unsafe_allow_html=True)
    st.markdown("학회/저널을 추천해드립니다")

    topic = st.text_input("궁금한 주제", placeholder="예: AI, Robotics, Education...")

    col1, col2 = st.columns([3, 1])
    with col1:
        suggest_clicked = st.button("추천 받기", use_container_width=True)
    with col2:
        clear_clicked = st.button("초기화", use_container_width=True)

    suggest_box = st.empty()

    if clear_clicked:
        suggest_box.empty()

    if suggest_clicked and topic.strip():
        with st.spinner("검색 중..."):
            chat = ChatUpstage(
                api_key=os.getenv("UPSTAGE_API_KEY"),
                model="solar-pro3",
                reasoning_effort="low",
            )

            prompt = f"""
            주제: {topic}

            이 주제와 가장 관련 있는 세계적으로 유명한 학회 또는 저널 이름을 3~5개 제시하라.
            조건:
            - 약어 위주로
            - 한 줄에 하나씩
            - 설명 없이 이름만
            """
            res = chat.invoke([HumanMessage(content=prompt)])
            suggest_box.text(res.content)

    st.markdown("<hr style='margin: 0.7rem 0; border: none; border-top: 1px solid #ddd;' />", unsafe_allow_html=True)

    venue_input = st.text_area(
        "원하는 학회 / 저널을 입력하세요",
        value=default_venues,
        height=80,
        help="한 줄에 하나씩 입력",
        placeholder="예: NeurIPS..."
    )
    st.markdown("<hr style='margin: 0.7rem 0; border: none; border-top: 1px solid #ddd;' />", unsafe_allow_html=True)
    time_choice = st.radio(
        "발송 시간",
        ["08:00", "12:00", "17:00", "21:00"],
        index=["08:00", "12:00", "17:00", "21:00"].index(default_time),
    )

    save_clicked = st.button("구독 설정 저장", use_container_width=True)

    if save_clicked:
        if not to_email or not venue_input.strip():
            st.warning("이메일과 학회를 입력해주세요.")
        else:
            venues_save = [v.strip() for v in venue_input.splitlines() if v.strip()]
            config = {
                "email": to_email,
                "venues": venues_save,
                "time": time_choice,
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            st.success(f"매일 {time_choice}에 만나요.")

venues = [v.strip() for v in venue_input.splitlines() if v.strip()]

st.divider()

st.markdown(
    """
    <div style="text-align:center; margin-top:3rem; margin-bottom:2rem;">
        <h2>오늘부터 최신 논문을 받아보세요</h2>
        <p>매일 선택한 학회의 논문을 요약해 메일로 보내드립니다</p>
    </div>
    """,
    unsafe_allow_html=True,
)

status = st.empty()
result = st.empty()

send_clicked = st.button("Upstage Solar Pro 3 함께 지금부터 공부하기", use_container_width=True)

if send_clicked:
    if not to_email or not venues:
        status.warning("사이드바에서 설정을 먼저 해주세요.")
    else:
        with st.spinner("arXiv에서 논문을 찾는 중..."):
            title, arxiv_id = run(to_email, venues)

        if title is None:
            status.error("조건에 맞는 논문을 찾지 못했습니다.")
        else:
            status.success("메일 전송 완료")
            result.markdown(
                f"""
            오늘 선택된 논문
            - {title}

            매일 {time_choice}시,

            선택하신 {", ".join(venues)} 중 하나의 논문을 정리해서 이메일로 보내드려요.
            """
            )
