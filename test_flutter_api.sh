#!/bin/bash

echo "🚀 플러터용 AcademyMap API 테스트 시작"
echo "========================================"

BASE_URL="http://127.0.0.1:8000/api"

# 1. 기본 학원 목록 테스트
echo -e "\n1️⃣ 기본 학원 목록 테스트"
echo "GET $BASE_URL/academies/?page=1&page_size=5"
curl -s "$BASE_URL/academies/?page=1&page_size=5" | jq '{count: .count, total_pages: .total_pages, first_academy: .results[0].상호명}' || echo "❌ 기본 목록 조회 실패"

# 2. 과목 필터링 테스트 - 수학
echo -e "\n2️⃣ 수학 과목 필터링 테스트"
echo "POST $BASE_URL/filtered_academies (수학 필터)"
MATH_COUNT=$(curl -s -X POST "$BASE_URL/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["수학"]
  }' | jq '. | length')
echo "수학 학원 수: $MATH_COUNT"

# 3. 과목 필터링 테스트 - 영어
echo -e "\n3️⃣ 영어 과목 필터링 테스트" 
echo "POST $BASE_URL/filtered_academies (영어 필터)"
ENGLISH_COUNT=$(curl -s -X POST "$BASE_URL/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9, 
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["영어"]
  }' | jq '. | length')
echo "영어 학원 수: $ENGLISH_COUNT"

# 4. 전체 과목 필터링 테스트
echo -e "\n4️⃣ 전체 과목 필터링 테스트"
echo "POST $BASE_URL/filtered_academies (전체 필터)"
ALL_COUNT=$(curl -s -X POST "$BASE_URL/filtered_academies" \
  -H "Content-Type: application/json" \
  -d '{
    "swLat": 37.5,
    "swLng": 126.9,
    "neLat": 37.6,
    "neLng": 127.1,
    "subjects": ["전체"]
  }' | jq '. | length')
echo "전체 학원 수: $ALL_COUNT"

# 5. 근처 학원 테스트 (강남역)
echo -e "\n5️⃣ 근처 학원 테스트 (강남역)"
echo "GET $BASE_URL/academies/nearby/?lat=37.498095&lng=127.02761&radius=1.0&limit=5"
curl -s "$BASE_URL/academies/nearby/?lat=37.498095&lng=127.02761&radius=1.0&limit=5" | jq '{count: (.results | length), first_academy: .results[0].상호명}' || echo "❌ 근처 학원 조회 실패"

# 6. 검색 테스트
echo -e "\n6️⃣ 검색 테스트 (수학)"
echo "GET $BASE_URL/academies/search/?q=수학&limit=3"
curl -s "$BASE_URL/academies/search/?q=수학&limit=3" | jq '{count: (.results | length), first_result: .results[0].상호명}' || echo "❌ 검색 실패"

# 7. 학원 상세 정보 테스트
echo -e "\n7️⃣ 학원 상세 정보 테스트"
FIRST_ID=$(curl -s "$BASE_URL/academies/?page=1&page_size=1" | jq '.results[0].id')
echo "GET $BASE_URL/academies/$FIRST_ID/"
curl -s "$BASE_URL/academies/$FIRST_ID/" | jq '{id: .id, name: .상호명, address: .도로명주소}' || echo "❌ 상세 정보 조회 실패"

# 8. 인기 학원 테스트
echo -e "\n8️⃣ 인기 학원 테스트"
echo "GET $BASE_URL/academies/popular/?limit=3"
curl -s "$BASE_URL/academies/popular/?limit=3" | jq '{count: (.results | length), first_popular: .results[0].상호명}' || echo "❌ 인기 학원 조회 실패"

# 9. 메타데이터 테스트
echo -e "\n9️⃣ 메타데이터 테스트"
echo "GET $BASE_URL/categories/"
curl -s "$BASE_URL/categories/" | jq '.subjects[0:5]' || echo "❌ 카테고리 조회 실패"

echo "GET $BASE_URL/regions/"
curl -s "$BASE_URL/regions/" | jq '.regions[0:3]' || echo "❌ 지역 조회 실패"

echo "GET $BASE_URL/stats/"
curl -s "$BASE_URL/stats/" | jq '{total_academies: .total_academies, top_subject: .subject_stats[0]}' || echo "❌ 통계 조회 실패"

# 10. 자동완성 테스트
echo -e "\n🔟 자동완성 테스트"
echo "GET $BASE_URL/autocomplete/?q=수학"
curl -s "$BASE_URL/autocomplete/?q=수학" | jq '.suggestions[0:3]' || echo "❌ 자동완성 실패"

echo -e "\n✅ 플러터용 API 테스트 완료!"
echo "========================================"

# 필터링 결과 요약
echo -e "\n📊 필터링 테스트 결과 요약:"
echo "- 수학 학원: $MATH_COUNT개"
echo "- 영어 학원: $ENGLISH_COUNT개" 
echo "- 전체 학원: $ALL_COUNT개"

if [ "$MATH_COUNT" -gt 0 ] && [ "$ENGLISH_COUNT" -gt 0 ] && [ "$ALL_COUNT" -gt 0 ]; then
    echo "✅ 과목 필터링이 정상적으로 작동합니다!"
else
    echo "❌ 과목 필터링에 문제가 있습니다."
fi