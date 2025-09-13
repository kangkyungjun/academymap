#!/usr/bin/env python
import requests
import json

# Django 서버가 실행 중이어야 함
url = "http://127.0.0.1:8000/api/filtered_academies"

print("=== 다중 필터 시스템 테스트 ===")

# 테스트 1: 단일 과목 선택 (수학)
payload1 = {
    "swLat": 37.4,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["수학"],
    "priceMin": 0,
    "priceMax": 2000000,
    "filterMode": "OR",
    "ageGroups": [],
    "shuttleFilter": False
}

print("1️⃣ 테스트 1: 수학 학원만 선택 (OR 모드)")
response1 = requests.post(url, json=payload1)
if response1.status_code == 200:
    data1 = response1.json()
    print(f"   결과: {len(data1) if isinstance(data1, list) else 'N/A'}개 학원 발견")
else:
    print(f"   에러: {response1.status_code}")

# 테스트 2: 다중 과목 선택 (수학 + 영어, OR 모드)
payload2 = {
    "swLat": 37.4,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["수학", "영어"],
    "priceMin": 0,
    "priceMax": 2000000,
    "filterMode": "OR",
    "ageGroups": [],
    "shuttleFilter": False
}

print("\n2️⃣ 테스트 2: 수학 + 영어 학원 (OR 모드)")
response2 = requests.post(url, json=payload2)
if response2.status_code == 200:
    data2 = response2.json()
    print(f"   결과: {len(data2) if isinstance(data2, list) else 'N/A'}개 학원 발견")
else:
    print(f"   에러: {response2.status_code}")

# 테스트 3: 다중 과목 선택 (수학 + 영어, AND 모드)
payload3 = {
    "swLat": 37.4,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["수학", "영어"],
    "priceMin": 0,
    "priceMax": 2000000,
    "filterMode": "AND",
    "ageGroups": [],
    "shuttleFilter": False
}

print("\n3️⃣ 테스트 3: 수학 + 영어 학원 (AND 모드)")
response3 = requests.post(url, json=payload3)
if response3.status_code == 200:
    data3 = response3.json()
    print(f"   결과: {len(data3) if isinstance(data3, list) else 'N/A'}개 학원 발견")
else:
    print(f"   에러: {response3.status_code}")

# 결과 비교
print("\n📊 필터 모드 비교:")
if 'data1' in locals() and isinstance(data1, list):
    print(f"   수학만: {len(data1)}개")
if 'data2' in locals() and isinstance(data2, list):
    print(f"   수학+영어 (OR): {len(data2)}개")
if 'data3' in locals() and isinstance(data3, list):
    print(f"   수학+영어 (AND): {len(data3)}개")

print(f"\n✅ 예상 결과: OR 모드 ≥ AND 모드 (수학+영어 OR가 더 많은 결과)")