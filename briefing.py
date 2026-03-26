#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 일일 업무 브리핑 프로그램 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  매일 아침 실행하면 오늘의 날씨, 증시,
  주요 뉴스를 한눈에 확인할 수 있어요!

  실행 방법:
    python briefing.py

  필요 라이브러리 설치:
    pip install requests

  데이터 출처:
    - 날씨: Open-Meteo (무료, API 키 불필요, 전일 비교 포함)
    - 증시: Stooq + CoinGecko + ExchangeRate API (모두 무료)
    - 뉴스: Google News RSS (무료)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import requests
import json
import datetime
import webbrowser
import os
from xml.etree import ElementTree as ET

# ============================================================
# ⚙️ 설정값 (원하는 대로 변경하세요!)
# ============================================================
CITY_KR = "서울"        # 날씨 표시용 도시 이름 (한국어)
LAT    = 37.5665        # 날씨 조회 위도  (서울 기준)
LON    = 126.9780       # 날씨 조회 경도  (서울 기준)


# ============================================================
# 1. 🌤️ 날씨 정보 수집 (Open-Meteo 무료 API)
#    - 현재 기온·체감·습도·풍속
#    - 전일 평균 기온과의 비교 (▲/▼ X°C)
#    - 오늘 강수 예보 기반 우산 필요 여부
# ============================================================
def get_weather():
    """
    Open-Meteo API로 현재 날씨와 전일 비교 데이터를 가져옵니다.
    WMO 표준 날씨 코드를 사용하며 API 키가 필요 없습니다.
    past_days=1 파라미터로 어제 데이터를 함께 받아 전일 대비를 계산합니다.
    """
    # WMO 날씨 코드 → (한국어 설명, 이모지) 매핑
    WMO = {
        0:  ("맑음",         "☀️"),
        1:  ("대체로 맑음",  "🌤️"),
        2:  ("구름 많음",    "⛅"),
        3:  ("흐림",         "☁️"),
        45: ("안개",         "🌫️"),
        48: ("짙은 안개",    "🌫️"),
        51: ("이슬비",       "🌦️"),
        53: ("보통 이슬비",  "🌦️"),
        55: ("강한 이슬비",  "🌧️"),
        61: ("가벼운 비",    "🌧️"),
        63: ("비",           "🌧️"),
        65: ("강한 비",      "🌧️"),
        71: ("가벼운 눈",    "❄️"),
        73: ("눈",           "❄️"),
        75: ("강한 눈",      "❄️"),
        77: ("눈송이",       "❄️"),
        80: ("소나기",       "🌦️"),
        81: ("보통 소나기",  "🌧️"),
        82: ("강한 소나기",  "🌧️"),
        85: ("눈 소나기",    "🌨️"),
        86: ("강한 눈 소나기","🌨️"),
        95: ("뇌우",         "⛈️"),
        96: ("우박 뇌우",    "⛈️"),
        99: ("강한 우박 뇌우","⛈️"),
    }
    # 우산이 필요한 날씨 코드 집합
    RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
    SNOW_CODES = {71, 73, 75, 77, 85, 86}

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            f"&current=temperature_2m,apparent_temperature,"
            f"relative_humidity_2m,wind_speed_10m,weather_code,precipitation"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum"
            f"&past_days=1"          # 어제 데이터 포함
            f"&timezone=Asia%2FSeoul"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        cur   = data["current"]
        daily = data["daily"]

        temp_now   = round(cur["temperature_2m"], 1)
        feels_like = round(cur["apparent_temperature"], 1)
        humidity   = cur["relative_humidity_2m"]
        wind       = round(cur["wind_speed_10m"], 1)
        wcode      = int(cur["weather_code"])

        desc, icon = WMO.get(wcode, ("알 수 없음", "🌈"))

        # ── 전일 대비 기온 계산 ──────────────────────────────
        # past_days=1이면 daily 배열의 [0]=어제, [1]=오늘
        y_max = daily["temperature_2m_max"][0]
        y_min = daily["temperature_2m_min"][0]
        y_avg = round((y_max + y_min) / 2, 1)
        diff  = round(temp_now - y_avg, 1)

        if diff > 0:
            diff_str   = f"▲ {diff}°C 높음"
            diff_color = "up"
        elif diff < 0:
            diff_str   = f"▼ {abs(diff)}°C 낮음"
            diff_color = "down"
        else:
            diff_str   = "전일과 동일"
            diff_color = "neutral"

        # ── 우산 필요 여부 판단 ──────────────────────────────
        # 오늘 예상 강수량 (daily[1])
        today_rain = daily["precipitation_sum"][1] \
            if len(daily["precipitation_sum"]) > 1 else 0

        needs_umbrella = (wcode in RAIN_CODES) or (today_rain and today_rain > 0.3)

        if needs_umbrella:
            tip = f"☂️ 우산을 챙기세요! (오늘 예상 강수량 {today_rain:.1f}mm)"
        elif wcode in SNOW_CODES:
            tip = "🧥 눈이 올 수 있어요. 따뜻하게 입으세요!"
        elif temp_now <= 0:
            tip = "🧥 매우 추워요. 두꺼운 외투 필수!"
        elif temp_now <= 10:
            tip = "🧣 쌀쌀해요. 겉옷을 챙기세요!"
        elif temp_now >= 30:
            tip = "💧 더워요! 수분 보충 잊지 마세요."
        else:
            tip = "😊 오늘 날씨가 쾌적해요!"

        return {
            "success":    True,
            "icon":       icon,
            "temp":       temp_now,
            "feels_like": feels_like,
            "desc":       desc,
            "humidity":   humidity,
            "wind":       wind,
            "tip":        tip,
            "diff_str":   diff_str,    # 전일 대비 문자열 (예: "▲ 3.2°C 높음")
            "diff_color": diff_color,  # "up" / "down" / "neutral"
            "y_avg":      y_avg,       # 전일 평균 기온
        }

    except Exception as e:
        print(f"  ⚠️  날씨 수집 실패: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 2. 📈 증시 데이터 수집
#    - 주가 지수: Yahoo Finance (크럼 방식, 더 안정적)
#    - 비트코인: CoinGecko (완전 무료, API 키 불필요)
#    - 환율: ExchangeRate API (완전 무료, API 키 불필요)
# ============================================================
def _make_stock_item(name, flag, price_str, change_str, color):
    """증시 항목 딕셔너리를 만드는 헬퍼 함수"""
    return {"name": name, "flag": flag,
            "price": price_str, "change": change_str, "color": color}


def _direction(change):
    """변화량에 따라 방향 기호와 색상 클래스를 반환"""
    if change > 0:
        return "▲", "up"
    elif change < 0:
        return "▼", "down"
    return "—", "neutral"


def get_stock_indices():
    """
    Stooq에서 KOSPI, NASDAQ, S&P 500 일봉 데이터를 가져옵니다.
    Stooq은 CSV 형태로 데이터를 무료 제공하며, 인증이 필요 없습니다.
    최근 2거래일 데이터로 전일 대비 등락을 계산합니다.
    """
    # Stooq 심볼: 소문자 사용
    symbols = {
        "^ks11": ("KOSPI",   "🇰🇷"),
        "^ndq":  ("NASDAQ",  "🇺🇸"),
        "^spx":  ("S&P 500", "🇺🇸"),
    }
    results = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for symbol, (name, flag) in symbols.items():
        try:
            # Stooq 일봉 CSV API (최근 수십 거래일 반환)
            url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()

            lines = r.text.strip().split("\n")
            # 줄 구성: [0]=헤더(Date,Open,High,Low,Close,Volume), [1..]=데이터
            if len(lines) < 3:
                print(f"  ⚠️  {name}: 데이터 부족")
                continue

            # 가장 최근 거래일과 그 전날 데이터
            latest = lines[-1].split(",")
            prev   = lines[-2].split(",")

            close      = float(latest[4])   # Close 가격
            prev_close = float(prev[4])
            change     = close - prev_close
            change_pct = (change / prev_close) * 100

            d, color = _direction(change)
            results.append(_make_stock_item(
                name, flag,
                f"{close:,.2f}",
                f"{d} {abs(change):.2f} ({abs(change_pct):.2f}%)",
                color
            ))

        except Exception as e:
            print(f"  ⚠️  {name} 수집 실패: {e}")

    return results


def get_bitcoin_price():
    """
    CoinGecko API로 비트코인 시세를 가져옵니다.
    완전 무료이며 API 키가 필요 없습니다.
    """
    try:
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()["bitcoin"]
        price = data["usd"]
        change_pct = data["usd_24h_change"]
        d, color = _direction(change_pct)
        return _make_stock_item(
            "비트코인", "₿",
            f"${price:,.0f}",
            f"{d} {abs(change_pct):.2f}% (24h)",
            color
        )
    except Exception as e:
        print(f"  ⚠️  비트코인 시세 수집 실패: {e}")
        return None


def get_exchange_rate():
    """
    ExchangeRate API로 달러/원 환율을 가져옵니다.
    완전 무료이며 API 키가 필요 없습니다.
    """
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        r.raise_for_status()
        krw = r.json()["rates"]["KRW"]
        return _make_stock_item(
            "달러/원", "💱",
            f"₩{krw:,.1f}",
            "— 실시간 환율",
            "neutral"
        )
    except Exception as e:
        print(f"  ⚠️  환율 수집 실패: {e}")
        return None


def get_stock_data():
    """증시, 비트코인, 환율을 통합해서 반환합니다."""
    results = []
    results.extend(get_stock_indices())

    btc = get_bitcoin_price()
    if btc:
        results.append(btc)

    fx = get_exchange_rate()
    if fx:
        results.append(fx)

    return {"success": len(results) > 0, "data": results}


# ============================================================
# 3. 📰 뉴스 수집 (Google News RSS)
#    구글 뉴스 RSS는 별도 인증 없이 안정적으로 사용할 수 있습니다.
# ============================================================
def get_news():
    """
    Google News RSS 피드에서 최신 한국어 뉴스 헤드라인을 가져옵니다.
    RSS는 XML 기반 뉴스 구독 표준으로, 구글 뉴스는 API 키 없이 무료로 사용 가능합니다.
    """
    # Google News RSS: 검색어별 최신 뉴스
    rss_feeds = [
        ("경제",   "https://news.google.com/rss/search?q=한국경제&hl=ko&gl=KR&ceid=KR:ko"),
        ("국제",   "https://news.google.com/rss/search?q=국제뉴스&hl=ko&gl=KR&ceid=KR:ko"),
        ("IT",     "https://news.google.com/rss/search?q=IT기술인공지능&hl=ko&gl=KR&ceid=KR:ko"),
    ]

    news_list = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for category, rss_url in rss_feeds:
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)

            # 각 피드에서 최신 기사 2개씩 추출
            for item in root.findall(".//item")[:2]:
                title_el = item.find("title")
                link_el  = item.find("link")

                raw_title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link      = link_el.text.strip()  if link_el  is not None and link_el.text  else "#"

                # Google News RSS 제목 형식: "기사 제목 - 언론사명"  → 언론사명 제거
                title = raw_title.rsplit(" - ", 1)[0] if " - " in raw_title else raw_title

                if title:
                    news_list.append({
                        "title":    title,
                        "link":     link,
                        "category": category,
                    })

        except Exception as e:
            print(f"  ⚠️  뉴스({category}) 수집 실패: {e}")
            continue

    return {"success": len(news_list) > 0, "data": news_list[:6]}


# ============================================================
# 4. 🖥️ HTML 브리핑 리포트 생성
# ============================================================
def get_greeting():
    """현재 시간에 맞는 인사말 반환"""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning! ☀️"
    elif 12 <= hour < 18:
        return "Good Afternoon! 🌤️"
    elif 18 <= hour < 22:
        return "Good Evening! 🌇"
    else:
        return "안녕하세요! 🌙"


def generate_html(weather, stocks, news):
    """수집한 데이터를 받아 브리핑 HTML 리포트를 생성합니다."""

    now = datetime.datetime.now()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    date_str = f"{now.year}년 {now.month}월 {now.day}일 ({weekdays[now.weekday()]})"
    time_str = now.strftime("%H:%M")
    greeting = get_greeting()

    # ── 날씨 섹션 HTML ──────────────────────────────────────
    if weather["success"]:
        weather_html = f"""
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">현재 기온</span>
                <span class="info-value temp">{weather['temp']}°C</span>
            </div>
            <div class="info-item">
                <span class="info-label">체감 온도</span>
                <span class="info-value">{weather['feels_like']}°C</span>
            </div>
            <div class="info-item">
                <span class="info-label">전일 대비 (어제 평균 {weather['y_avg']}°C)</span>
                <span class="info-value diff-{weather['diff_color']}">{weather['diff_str']}</span>
            </div>
            <div class="info-item">
                <span class="info-label">습도 / 풍속</span>
                <span class="info-value">{weather['humidity']}% · {weather['wind']} km/h</span>
            </div>
        </div>
        <div class="weather-desc">{weather['icon']} {weather['desc']}</div>
        <div class="weather-tip">{weather['tip']}</div>
        """
    else:
        weather_html = "<p class='error-msg'>날씨 정보를 불러오지 못했어요 😥</p>"

    # ── 증시 섹션 HTML ──────────────────────────────────────
    if stocks["success"] and stocks["data"]:
        rows = ""
        for s in stocks["data"]:
            rows += f"""
            <div class="stock-row">
                <span class="stock-name">{s['flag']} {s['name']}</span>
                <span class="stock-price">{s['price']}</span>
                <span class="stock-change {s['color']}">{s['change']}</span>
            </div>
            """
        stocks_html = f'<div class="stock-list">{rows}</div>'
    else:
        stocks_html = "<p class='error-msg'>시장 데이터를 불러오지 못했어요 😥</p>"

    # ── 뉴스 섹션 HTML ──────────────────────────────────────
    if news["success"] and news["data"]:
        items = ""
        for n in news["data"]:
            items += f"""
            <a href="{n['link']}" target="_blank" class="news-item">
                <span class="news-badge">{n['category']}</span>
                <span class="news-title">{n['title']}</span>
            </a>
            """
        news_html = f'<div class="news-list">{items}</div>'
    else:
        news_html = "<p class='error-msg'>뉴스를 불러오지 못했어요 😥</p>"

    # ── 전체 HTML 조합 ──────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>일일 업무 브리핑 · {date_str}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      padding: 24px 16px;
    }}

    .container {{
      max-width: 920px;
      margin: 0 auto;
    }}

    /* ── 헤더 ── */
    .header {{
      text-align: center;
      padding: 48px 0 36px;
      border-bottom: 1px solid #1e293b;
      margin-bottom: 28px;
    }}
    .header .greeting {{
      font-size: 13px;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: #64748b;
      margin-bottom: 10px;
    }}
    .header .date {{
      font-size: 24px;
      font-weight: 700;
      color: #f1f5f9;
      margin-bottom: 6px;
    }}
    .header .time {{
      font-size: 56px;
      font-weight: 800;
      background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1;
    }}

    /* ── 카드 레이아웃 ── */
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 20px;
    }}
    .card {{
      background: #1e293b;
      border-radius: 18px;
      padding: 24px;
      border: 1px solid #334155;
    }}
    .card-full {{ grid-column: span 2; }}
    .card-title {{
      font-size: 12px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 18px;
    }}

    /* ── 날씨 ── */
    .info-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 14px;
    }}
    .info-item {{
      background: #0f172a;
      border-radius: 12px;
      padding: 14px;
    }}
    .info-label {{
      display: block;
      font-size: 11px;
      color: #475569;
      margin-bottom: 5px;
    }}
    .info-value {{
      display: block;
      font-size: 22px;
      font-weight: 700;
      color: #f1f5f9;
    }}
    .info-value.temp {{
      font-size: 30px;
      background: linear-gradient(135deg, #38bdf8, #60a5fa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
    .info-value.diff-up      {{ color: #f87171; font-size: 15px; font-weight: 700; }}
    .info-value.diff-down    {{ color: #34d399; font-size: 15px; font-weight: 700; }}
    .info-value.diff-neutral {{ color: #94a3b8; font-size: 15px; font-weight: 600; }}
    .weather-desc {{
      font-size: 15px;
      color: #cbd5e1;
      margin-bottom: 10px;
    }}
    .weather-tip {{
      font-size: 13px;
      color: #94a3b8;
      background: #0f172a;
      padding: 10px 14px;
      border-radius: 10px;
      border-left: 3px solid #3b82f6;
    }}

    /* ── 증시 ── */
    .stock-list {{ display: flex; flex-direction: column; gap: 8px; }}
    .stock-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: #0f172a;
      border-radius: 10px;
    }}
    .stock-name {{
      font-size: 14px;
      font-weight: 600;
      color: #e2e8f0;
      flex: 1;
    }}
    .stock-price {{
      font-size: 14px;
      font-weight: 700;
      color: #f1f5f9;
      margin: 0 12px;
    }}
    .stock-change {{
      font-size: 12px;
      font-weight: 700;
      text-align: right;
      min-width: 130px;
    }}
    .stock-change.up      {{ color: #34d399; }}
    .stock-change.down    {{ color: #f87171; }}
    .stock-change.neutral {{ color: #64748b; }}

    /* ── 뉴스 ── */
    .news-list {{ display: flex; flex-direction: column; gap: 8px; }}
    .news-item {{
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 14px 16px;
      background: #0f172a;
      border-radius: 12px;
      text-decoration: none;
      transition: background 0.15s;
    }}
    .news-item:hover {{ background: #172033; }}
    .news-badge {{
      font-size: 11px;
      font-weight: 700;
      color: #60a5fa;
      background: rgba(96, 165, 250, 0.12);
      padding: 3px 9px;
      border-radius: 20px;
      white-space: nowrap;
      margin-top: 1px;
    }}
    .news-title {{
      font-size: 14px;
      color: #cbd5e1;
      line-height: 1.6;
    }}

    /* ── 기타 ── */
    .error-msg {{ color: #475569; font-size: 14px; padding: 12px 0; }}

    .footer {{
      text-align: center;
      padding: 28px 0;
      color: #334155;
      font-size: 12px;
      border-top: 1px solid #1e293b;
      margin-top: 8px;
    }}

    /* ── 반응형 ── */
    @media (max-width: 640px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .card-full {{ grid-column: span 1; }}
      .header .time {{ font-size: 40px; }}
      .stock-change {{ min-width: 100px; font-size: 11px; }}
    }}
  </style>
</head>
<body>
  <div class="container">

    <!-- 헤더 -->
    <div class="header">
      <div class="greeting">{greeting}</div>
      <div class="date">{date_str}</div>
      <div class="time">{time_str}</div>
    </div>

    <!-- 날씨 & 증시 -->
    <div class="grid">
      <div class="card">
        <div class="card-title">🌤️ 오늘의 날씨 · {CITY_KR}</div>
        {weather_html}
      </div>

      <div class="card">
        <div class="card-title">📈 시장 동향</div>
        {stocks_html}
      </div>
    </div>

    <!-- 뉴스 -->
    <div class="grid">
      <div class="card card-full">
        <div class="card-title">📰 주요 뉴스</div>
        {news_html}
      </div>
    </div>

    <div class="footer">
      ⏱ {now.strftime('%Y-%m-%d %H:%M:%S')} 기준 &nbsp;|&nbsp;
      데이터 출처: wttr.in · Yahoo Finance · 연합뉴스
    </div>

  </div>
</body>
</html>
"""
    return html


# ============================================================
# 5. 🚀 메인 실행
# ============================================================
def main():
    print()
    print("=" * 52)
    print("   📊  일일 업무 브리핑 생성을 시작합니다...")
    print("=" * 52)

    # 데이터 수집
    print("\n  🌤  날씨 정보 수집 중...")
    weather = get_weather()

    print("  📈  증시 데이터 수집 중...")
    stocks = get_stock_data()

    print("  📰  뉴스 수집 중...")
    news = get_news()

    # HTML 생성
    print("\n  📄  브리핑 리포트 생성 중...")
    html_content = generate_html(weather, stocks, news)

    # 파일 저장 (이 스크립트와 같은 폴더에 저장)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefing_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 브라우저로 열기
    print(f"  ✅  완료! 브라우저를 여는 중...")
    webbrowser.open(f"file:///{output_path.replace(os.sep, '/')}")

    print(f"\n  📁  저장 위치: {output_path}")
    print("=" * 52)
    print()


if __name__ == "__main__":
    main()
