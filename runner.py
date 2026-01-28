import json, datetime
from agent import run

CONFIG_FILE = "config.json"

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    cfg = json.load(f)

now = datetime.datetime.now().strftime("%H:%M")

# 설정된 시간이 아닐 경우 아무것도 하지 않음
if now != cfg["time"]:
    exit()

to_email = cfg["email"]
venues = cfg["venues"]

title, arxiv_id = run(to_email, venues)

if title is None:
    print("조건에 맞는 논문이 없음")
else:
    print("전송 완료:", title)
