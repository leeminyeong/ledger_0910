# 실행 권한 관련 PowerShell 명령어 (개발자 참고용)
# Set-ExecutionPolicy RemoteSigned
# venv\Scripts\Activate
# Set-ExecutionPolicy Restricted

from flask import Flask, session, render_template, request, redirect, url_for
from dotenv import load_dotenv
import json
import os
import sqlite3
from datetime import datetime
import requests
import time
from bs4 import BeautifulSoup



# Flask 앱 생성
app = Flask(__name__, template_folder='templates')

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

# SQLite 데이터베이스 파일 경로
#DB_PATH = "database.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# BTC 가격 캐시 저장소 (30초 내 재요청 방지용)
price_cache = {
    "usd": {"value": 0, "timestamp": 0},
    "krw": {"value": 0, "timestamp": 0}
}


# DB에 새로운 수령 내역 삽입
def insert_entry(amount, btc):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO entries (date, amount, btc) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), amount, btc)
    )
    conn.commit()
    conn.close()

@app.route("/receive", methods=["POST"])
def receive():
    if request.method == "POST":
        password = request.form.get("password")
        if password != os.getenv("LOGIN_PASSWORD"):
            # 비밀번호 틀리면 URL 파라미터로 전달
            return redirect(url_for("index", error="wrong_password"))
    amount = request.form["amount"]
    btc = request.form["btc"]
    # 여기서 DB에 저장하는 로직 실행
    insert_entry(amount, btc)
    
    return redirect("/")

# BTC 시세 가져오기
def get_upbit_btc_price(param):
    try:
        url = "https://api.upbit.com/v1/ticker?markets="+param+"-BTC"
        res = requests.get(url, timeout=3)
        data = res.json()

        return data[0]['trade_price']  # 현재가 반환
    except Exception as e:
        print("💥 업비트 시세 조회 실패:", e)
        return 0

    except Exception as e:
        print("💥 BTC 시세 조회 실패:", e)
        return price_cache[param]["value"] or 1  # 실패 시 마지막 값 또는 1 반환

# 환율정보 가져오기
def get_naver_usd_krw():
    url = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # <em class="no_up"> 안의 모든 <span>을 모아서 문자열로 연결
    em_tag = soup.select_one("em.no_up")
    if em_tag:
        number_str = ''.join(span.text for span in em_tag.select("span"))
        try:
            return float(number_str.replace(",", ""))
        except ValueError:
            return 0
    return 0


# 대시보드 요약 정보 계산 함수
def get_summary():
    # DB에서 총 수령 금액, BTC 수량 조회
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(amount), SUM(btc) FROM entries")
    row = c.fetchone()
    conn.close()

    # 기본 값 설정
    total_amount = row[0] or 0
    total_btc = row[1] or 0

    # 시세 조회 (USD, KRW) -- 수정수정했수정
    price = get_upbit_btc_price("USDT")
    k_price = get_upbit_btc_price("KRW")

    # 현재 자산 평가
    valuation = total_btc * price  # USD 기준 평가액
    rate = ((valuation - total_amount) / total_amount * 100) if total_amount else 0  # 수익률

    # 환율
    c_rate = get_naver_usd_krw()

    # 한화 기준 평가
    k_valuation = valuation * c_rate
    k_total_amount = total_amount * c_rate
    k_gap =  k_valuation -  k_total_amount

    return {
        "total_amount": total_amount,
        "total_btc": total_btc,
        "price": price,
        "valuation": valuation,
        "rate": rate,
        "k_valuation": k_valuation,
        "k_total_amount": k_total_amount,
        "k_gap": k_gap,
        "k_price": k_price
    }


# 최근 수령 내역 목록 조회 (최신순 정렬)
def fetch_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT date, amount, btc, id FROM entries ORDER BY id DESC")
    entries = c.fetchall()
    conn.close()
    return entries

# 메인 페이지: 수령 내역 + 요약 정보 표시
@app.route("/")
def index():

    if not session.get("logged_in"):
        return redirect("/login")

    entries = fetch_entries()
    summary = get_summary()
    return render_template("index.html", entries=entries, summary=summary)

# 수령 정보 추가 처리
@app.route("/add", methods=["POST"])
def add():
    amount = request.form.get("amount")
    btc = request.form.get("btc")
    if amount and btc:
        insert_entry(float(amount), float(btc))
    return redirect("/")

@app.route("/edit/<int:id>", methods=["POST"])
def edit_entry(id):
    amount = float(request.form["amount"])
    btc = float(request.form["btc"])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE entries SET amount = ?, btc = ? WHERE id = ?", (amount, btc, id))
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete/<int:id>", methods=["POST"])
def delete_entry(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == os.getenv("LOGIN_PASSWORD"):
            session["logged_in"] = True
            return redirect("/")
        else:
            return render_template("login.html", error=True)
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("token", None)  # 토큰 제거
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)