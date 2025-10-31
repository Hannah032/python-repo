# file: morning_brief_bot.py
import os, asyncio, textwrap
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import feedparser  # RSS 파서
from dotenv import load_dotenv

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

KST = ZoneInfo("Asia/Seoul")
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
FEEDS = [u.strip() for u in os.getenv("FEEDS","").split(",") if u.strip()]
CITY = os.getenv("CITY", "Seoul")
LAT = os.getenv("LAT", "37.5665")
LON = os.getenv("LON", "126.9780")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

intents = discord.Intents.default()  # 기본이면 충분. 메시지 읽기 권한은 길드/채널 권한으로 커버
bot = commands.Bot(command_prefix="!", intents=intents)

def fetch_weather():
    """OpenWeather 현재 날씨 조회"""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": LAT, "lon": LON, "appid": OPENWEATHER_API_KEY,
        "units": "metric", "lang": "kr"
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    desc = data["weather"][0]["description"].capitalize()
    temp = round(data["main"]["temp"])
    feels = round(data["main"]["feels_like"])
    humidity = data["main"]["humidity"]
    wind = round(data["wind"].get("speed", 0))
    return {
        "desc": desc,
        "temp": temp,
        "feels": feels,
        "humidity": humidity,
        "wind": wind
    }

def fetch_headlines(limit=5):
    """RSS 피드에서 최근 기사 헤드라인 모으기"""
    items = []
    seen = set()
    for feed in FEEDS:
        parsed = feedparser.parse(feed)
        for e in parsed.entries[:limit*2]:
            title = (e.title or "").strip()
            link = getattr(e, "link", "").strip()
            if not title or not link: 
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append((title, link))
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break
    return items[:limit]

async def send_brief():
    """임베드로 아침 브리핑 전송"""
    ch = bot.get_channel(CHANNEL_ID)
    if ch is None:
        logging.error("채널을 찾을 수 없음. CHANNEL_ID 확인 필요")
        return

    # 데이터 수집
    try:
        w = fetch_weather()
    except Exception as e:
        logging.exception("날씨 조회 실패: %s", e)
        w = None

    headlines = []
    try:
        headlines = fetch_headlines(limit=5)
    except Exception as e:
        logging.exception("뉴스 조회 실패: %s", e)

    # 임베드 구성
    now = datetime.now(KST)
    title = f"☀️ 아침 브리핑 | {now.strftime('%Y-%m-%d (%a) %H:%M')}"
    embed = discord.Embed(title=title, color=0x2b90d9)

    if w:
        weather_text = f"{CITY}: {w['desc']}, {w['temp']}°C (체감 {w['feels']}°C), 습도 {w['humidity']}%, 바람 {w['wind']} m/s"
    else:
        weather_text = "날씨 정보를 불러오지 못했습니다."

    embed.add_field(name="🌤 날씨", value=weather_text, inline=False)

    if headlines:
        news_lines = [f"• [{t}]({u})" for t, u in headlines]
        embed.add_field(name="🗞 핵심 뉴스 Top 5", value="\n".join(news_lines), inline=False)
    else:
        embed.add_field(name="🗞 핵심 뉴스", value="뉴스를 불러오지 못했습니다.", inline=False)

    embed.set_footer(text="데이터: OpenWeather, BBC/연합뉴스TV RSS 등")

    await ch.send(embed=embed)
    logging.info("브리핑 전송 완료")

@bot.event
async def on_ready():
    logging.info("로그인: %s (%s)", bot.user, bot.user.id)
    # 매일 08:00 KST 스케줄
    sched = AsyncIOScheduler(timezone=str(KST))
    sched.add_job(send_brief, "cron", hour=8, minute=0)
    sched.start()
    # 봇 켜자마자 테스트 1회
    await asyncio.sleep(3)
    await send_brief()

# 선택: 수동 호출 슬래시 커맨드
@bot.tree.command(name="브리핑", description="바로 아침 브리핑 보내기")
async def brief_cmd(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    await send_brief()
    await interaction.followup.send("브리핑 전송 완료", ephemeral=True)

@bot.event
async def setup_hook():
    # 슬래시 커맨드 동기화
    await bot.tree.sync()

if __name__ == "__main__":
    if not DISCORD_TOKEN or not CHANNEL_ID:
        raise SystemExit("DISCORD_TOKEN/CHANNEL_ID 환경변수 확인 필요")
    bot.run(DISCORD_TOKEN)

print("TOKEN:", bool(DISCORD_TOKEN), "CHANNEL:", CHANNEL_ID)
