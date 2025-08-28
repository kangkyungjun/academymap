#!/usr/bin/env python
"""
전체 학원 데이터 재임포트 스크립트
Excel 파일(n_data.xlsx)의 98,651개 데이터를 모두 DB에 임포트
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academymap.settings')
django.setup()

from main.models import Data
from django.db import transaction

def clean_data(value):
    """데이터 정제 함수"""
    if pd.isna(value):
        return None
    if isinstance(value, str):
        return value.strip() if value.strip() else None
    return value

def convert_to_boolean(value):
    """문자열을 Boolean으로 변환"""
    if pd.isna(value) or value is None:
        return False
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    if isinstance(value, str):
        value = value.strip().lower()
        return value in ['true', '1', 'yes', 'y', '참', 'o', 'x'] and value not in ['false', '0', 'no', 'n', '거짓', '']
    
    return False

def import_full_data():
    """전체 데이터 임포트 메인 함수"""
    
    print("=" * 60)
    print("📊 AcademyMap 전체 데이터 재임포트 시작")
    print("=" * 60)
    
    # 1. Excel 파일 로드
    print("1️⃣ Excel 파일 로딩 중...")
    try:
        df = pd.read_excel('n_data.xlsx')
        print(f"   ✅ Excel 파일 로드 완료: {len(df):,}개 레코드")
    except Exception as e:
        print(f"   ❌ Excel 파일 로드 실패: {e}")
        return False
    
    # 2. 기존 데이터 백업 정보
    existing_count = Data.objects.count()
    print(f"2️⃣ 기존 DB 데이터: {existing_count:,}개")
    
    # 3. 데이터베이스 초기화 (기존 데이터 삭제)
    print("3️⃣ 기존 데이터 삭제 중...")
    with transaction.atomic():
        deleted_count = Data.objects.all().delete()[0]
        print(f"   ✅ 기존 데이터 삭제 완료: {deleted_count:,}개")
    
    # 4. 새 데이터 임포트
    print("4️⃣ 새 데이터 임포트 시작...")
    
    successful_imports = 0
    failed_imports = 0
    batch_size = 1000
    
    # 배치 처리로 메모리 효율성 향상
    total_batches = (len(df) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(df))
        batch_df = df.iloc[start_idx:end_idx]
        
        batch_objects = []
        
        for index, row in batch_df.iterrows():
            try:
                # Data 객체 생성
                academy = Data(
                    # 기본 정보
                    상가업소번호=clean_data(row.get('상가업소번호')),
                    상호명=clean_data(row.get('상호명')),
                    상권업종대분류코드=clean_data(row.get('상권업종대분류코드')),
                    상권업종대분류명=clean_data(row.get('상권업종대분류명')),
                    상권업종중분류명=clean_data(row.get('상권업종중분류명')),
                    상권업종소분류명=clean_data(row.get('상권업종소분류명')),
                    
                    # 주소 정보
                    시도명=clean_data(row.get('시도명')),
                    시군구명=clean_data(row.get('시군구명')),
                    행정동명=clean_data(row.get('행정동명')),
                    법정동명=clean_data(row.get('법정동명')),
                    지번주소=clean_data(row.get('지번주소')),
                    도로명주소=clean_data(row.get('도로명주소')),
                    
                    # 좌표 정보
                    경도=row.get('경도') if pd.notna(row.get('경도')) else None,
                    위도=row.get('위도') if pd.notna(row.get('위도')) else None,
                    
                    # 추가 정보
                    학원사진=clean_data(row.get('학원사진')),
                    대표원장=clean_data(row.get('대표원장')),
                    레벨테스트=clean_data(row.get('레벨테스트')),
                    강사=clean_data(row.get('강사')),
                    
                    # 대상 학년 (Boolean 필드들)
                    대상_유아=convert_to_boolean(row.get('대상_유아')),
                    대상_초등=convert_to_boolean(row.get('대상_초등')),
                    대상_중등=convert_to_boolean(row.get('대상_중등')),
                    대상_고등=convert_to_boolean(row.get('대상_고등')),
                    대상_특목고=convert_to_boolean(row.get('대상_특목고')),
                    대상_일반=convert_to_boolean(row.get('대상_일반')),
                    대상_기타=convert_to_boolean(row.get('대상_기타')),
                    
                    # 인증 정보
                    인증_명문대=convert_to_boolean(row.get('인증_명문대')),
                    인증_경력=convert_to_boolean(row.get('인증_경력')),
                    
                    # 학원 소개글
                    소개글=clean_data(row.get('소개글')),
                    
                    # 과목 분류 (Boolean 필드들)
                    과목_종합=convert_to_boolean(row.get('과목_종합')),
                    과목_수학=convert_to_boolean(row.get('과목_수학')),
                    과목_영어=convert_to_boolean(row.get('과목_영어')),
                    과목_과학=convert_to_boolean(row.get('과목_과학')),
                    과목_외국어=convert_to_boolean(row.get('과목_외국어')),
                    과목_예체능=convert_to_boolean(row.get('과목_예체능')),
                    과목_컴퓨터=convert_to_boolean(row.get('과목_컴퓨터')),
                    과목_논술=convert_to_boolean(row.get('과목_논술')),
                    과목_기타=convert_to_boolean(row.get('과목_기타')),
                    과목_독서실스터디카페=convert_to_boolean(row.get('과목_독서실스터디카페')),
                    
                    # 기타 정보
                    별점=row.get('별점') if pd.notna(row.get('별점')) else None,
                    전화번호=clean_data(row.get('전화번호')),
                    영업시간=clean_data(row.get('영업시간')),
                    셔틀버스=clean_data(row.get('셔틀버스')),
                    수강료=clean_data(row.get('수강료')),
                    수강료_평균=clean_data(row.get('수강료_평균')),
                )
                
                batch_objects.append(academy)
                successful_imports += 1
                
            except Exception as e:
                failed_imports += 1
                print(f"   ⚠️ 레코드 {index} 임포트 실패: {e}")
                continue
        
        # 배치 저장
        try:
            with transaction.atomic():
                Data.objects.bulk_create(batch_objects)
            
            progress = (batch_num + 1) / total_batches * 100
            print(f"   📈 진행률: {progress:.1f}% ({end_idx:,}/{len(df):,}) - 배치 {batch_num + 1}/{total_batches}")
            
        except Exception as e:
            failed_imports += len(batch_objects)
            print(f"   ❌ 배치 {batch_num + 1} 저장 실패: {e}")
    
    # 5. 결과 요약
    print("\n" + "=" * 60)
    print("📊 임포트 완료 결과")
    print("=" * 60)
    
    final_count = Data.objects.count()
    print(f"✅ 성공적으로 임포트: {successful_imports:,}개")
    print(f"❌ 실패한 레코드: {failed_imports:,}개")
    print(f"📊 최종 DB 레코드 수: {final_count:,}개")
    print(f"📈 임포트율: {(final_count / len(df) * 100):.1f}%")
    
    # 6. 데이터 검증
    print("\n6️⃣ 데이터 검증 중...")
    
    # 좌표 데이터 확인
    with_coords = Data.objects.filter(위도__isnull=False, 경도__isnull=False).count()
    print(f"   📍 좌표 정보 보유: {with_coords:,}개 ({with_coords/final_count*100:.1f}%)")
    
    # 과목별 분포 확인
    subjects = ['수학', '영어', '종합', '예체능', '과학']
    print("   📚 주요 과목별 학원 수:")
    for subject in subjects:
        count = Data.objects.filter(**{f'과목_{subject}': True}).count()
        print(f"      {subject}: {count:,}개")
    
    # 지역별 분포 확인 (상위 5개)
    from django.db.models import Count
    top_regions = Data.objects.values('시도명').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    print("   🗺️ 상위 지역별 학원 수:")
    for region in top_regions:
        print(f"      {region['시도명']}: {region['count']:,}개")
    
    print("\n🎉 전체 데이터 재임포트 완료!")
    return True

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = import_full_data()
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n⏱️ 소요 시간: {duration}")
    print(f"완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n✅ 모든 작업이 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 일부 작업에서 오류가 발생했습니다.")