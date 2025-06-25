from flask import Flask, render_template, request, redirect
import json
import os
import sqlite3
from datetime import datetime
import requests
import time
from bs4 import BeautifulSoup


    

def get_upbit_btc_price(param):
    try:
        url = "https://api.upbit.com/v1/ticker?markets="+param+"-BTC"
        res = requests.get(url, timeout=3)
        data = res.json()
        
        return data[0]['trade_price']  # 현재가 반환
    except Exception as e:
        print("💥 업비트 시세 조회 실패:", e)
        return 0

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

# 테스트 출력
print(get_naver_usd_krw())