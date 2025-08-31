#!/bin/bash

echo "📱 Flutter API 테스트 - 간단 버전"
echo "================================"

BASE_URL="http://127.0.0.1:8000"

# 1. 서버 연결 테스트
echo -e "\n🔗 서버 연결 테스트"
curl -s "$BASE_URL" | grep -q "AcademyMap" && echo "✅ 서버 연결됨" || echo "❌ 서버 연결 실패"

# 2. 수학 학원 필터링 테스트
echo -e "\n📚 수학 학원 필터링 테스트"
MATH_COUNT=$(curl -s -X POST "$BASE_URL/api/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["수학"]
  }' | jq '. | length')
echo "수학 학원 수: $MATH_COUNT개"

# 3. 영어 학원 필터링 테스트  
echo -e "\n🇺🇸 영어 학원 필터링 테스트"
ENGLISH_COUNT=$(curl -s -X POST "$BASE_URL/api/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["영어"]
  }' | jq '. | length')
echo "영어 학원 수: $ENGLISH_COUNT개"

# 4. 전체 학원 필터링 테스트
echo -e "\n🌐 전체 학원 필터링 테스트"
ALL_COUNT=$(curl -s -X POST "$BASE_URL/api/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["전체"]
  }' | jq '. | length')
echo "전체 학원 수: $ALL_COUNT개"

# 5. 첫 번째 수학 학원 정보 확인
echo -e "\n📋 첫 번째 수학 학원 정보"
curl -s -X POST "$BASE_URL/api/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["수학"]
  }' | jq -r '.[0] | "이름: \(.["상호명"]) / 주소: \(.["도로명주소"]) / 좌표: (\(.["위도"]), \(.["경도"]))"'

echo -e "\n📊 테스트 결과 요약:"
echo "- 수학 학원: $MATH_COUNT개"
echo "- 영어 학원: $ENGLISH_COUNT개"
echo "- 전체 학원: $ALL_COUNT개"

if [ "$MATH_COUNT" -gt 0 ] && [ "$ENGLISH_COUNT" -gt 0 ] && [ "$ALL_COUNT" -gt 0 ]; then
    echo "✅ Flutter API 테스트 성공! 필터링이 정상 작동합니다."
else
    echo "❌ Flutter API 테스트 실패"
fi

echo -e "\n🚀 Flutter 앱에서 사용할 수 있는 API 엔드포인트:"
echo "- POST $BASE_URL/api/filtered_academies (지역+과목 필터링)"
echo "- GET $BASE_URL (메인 지도 페이지)"
echo "- GET $BASE_URL/academy/<id> (학원 상세 정보)"