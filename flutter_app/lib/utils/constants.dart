import 'package:flutter/material.dart';

class AppConstants {
  // API 설정
  static const String apiBaseUrl = 'http://127.0.0.1:8000';
  static const String apiV1Path = '/api/v1';
  static const String enhancedApiPath = '/api/enhanced';
  
  // 색상 설정
  static const Color primaryColor = Color(0xFF2563EB); // Blue-600
  static const Color primaryColorDark = Color(0xFF1D4ED8); // Blue-700
  static const Color primaryColorLight = Color(0xFF3B82F6); // Blue-500
  static const Color secondaryColor = Color(0xFF10B981); // Emerald-500
  static const Color backgroundColor = Color(0xFFF8FAFC); // Slate-50
  static const Color surfaceColor = Colors.white;
  static const Color errorColor = Color(0xFFEF4444); // Red-500
  static const Color warningColor = Color(0xFFF59E0B); // Amber-500
  static const Color successColor = Color(0xFF10B981); // Emerald-500
  
  // 텍스트 색상
  static const Color textPrimary = Color(0xFF0F172A); // Slate-900
  static const Color textSecondary = Color(0xFF64748B); // Slate-500
  static const Color textDisabled = Color(0xFF94A3B8); // Slate-400
  
  // 간격 및 크기
  static const double paddingSmall = 8.0;
  static const double paddingMedium = 16.0;
  static const double paddingLarge = 24.0;
  static const double paddingXLarge = 32.0;
  
  static const double borderRadius = 12.0;
  static const double borderRadiusSmall = 8.0;
  static const double borderRadiusLarge = 16.0;
  
  // 텍스트 스타일 크기
  static const double fontSizeSmall = 12.0;
  static const double fontSizeMedium = 14.0;
  static const double fontSizeLarge = 16.0;
  static const double fontSizeXLarge = 18.0;
  static const double fontSizeXXLarge = 20.0;
  static const double fontSizeTitle = 24.0;
  static const double fontSizeHeading = 28.0;
  
  // 애니메이션 지속시간
  static const Duration animationDurationShort = Duration(milliseconds: 200);
  static const Duration animationDurationMedium = Duration(milliseconds: 300);
  static const Duration animationDurationLong = Duration(milliseconds: 500);
  
  // 지도 설정
  static const double defaultLatitude = 37.5665; // 서울시청 좌표
  static const double defaultLongitude = 126.9780;
  static const double defaultZoom = 11.0;
  static const double detailZoom = 15.0;
  
  // 검색 설정
  static const int searchDebounceMs = 500;
  static const int maxSearchResults = 20;
  static const int maxRecentSearches = 10;
  
  // 캐싱 설정
  static const Duration cacheExpiration = Duration(hours: 1);
  static const Duration imagesCacheExpiration = Duration(days: 7);
  
  // 페이지네이션
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;
  
  // 리스트 아이템 높이
  static const double listItemHeight = 120.0;
  static const double compactListItemHeight = 80.0;
  
  // 그림자
  static const List<BoxShadow> cardShadow = [
    BoxShadow(
      color: Color(0x0A000000),
      blurRadius: 8,
      offset: Offset(0, 2),
    ),
  ];
  
  static const List<BoxShadow> elevatedShadow = [
    BoxShadow(
      color: Color(0x14000000),
      blurRadius: 12,
      offset: Offset(0, 4),
    ),
  ];
  
  // 네트워크 설정
  static const Duration connectionTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 10);
  static const int maxRetries = 3;
  
  // 알림 설정
  static const String notificationChannelId = 'academymap_channel';
  static const String notificationChannelName = 'AcademyMap 알림';
  static const String notificationChannelDescription = 'AcademyMap 앱 알림';
  
  // 저장소 키
  static const String keyAccessToken = 'access_token';
  static const String keyRefreshToken = 'refresh_token';
  static const String keyUserData = 'user_data';
  static const String keySearchHistory = 'search_history';
  static const String keyFavoriteAcademies = 'favorite_academies';
  static const String keyAppSettings = 'app_settings';
  static const String keyLocationPermission = 'location_permission';
  static const String keyNotificationPermission = 'notification_permission';
  
  // 에러 메시지
  static const String errorNetworkConnection = '네트워크 연결을 확인해주세요.';
  static const String errorServerError = '서버 오류가 발생했습니다.';
  static const String errorUnknown = '알 수 없는 오류가 발생했습니다.';
  static const String errorLocationPermission = '위치 권한이 필요합니다.';
  static const String errorLocationService = '위치 서비스를 사용할 수 없습니다.';
  
  // 성공 메시지
  static const String successLogin = '로그인되었습니다.';
  static const String successLogout = '로그아웃되었습니다.';
  static const String successFavoriteAdded = '즐겨찾기에 추가되었습니다.';
  static const String successFavoriteRemoved = '즐겨찾기에서 제거되었습니다.';
  
  // 확인 메시지
  static const String confirmLogout = '로그아웃하시겠습니까?';
  static const String confirmDeleteAccount = '정말로 계정을 삭제하시겠습니까?';
  
  // 버튼 텍스트
  static const String buttonConfirm = '확인';
  static const String buttonCancel = '취소';
  static const String buttonSave = '저장';
  static const String buttonDelete = '삭제';
  static const String buttonEdit = '수정';
  static const String buttonAdd = '추가';
  static const String buttonSearch = '검색';
  static const String buttonFilter = '필터';
  static const String buttonRetry = '다시 시도';
  static const String buttonLogin = '로그인';
  static const String buttonLogout = '로그아웃';
  static const String buttonSignUp = '회원가입';
  
  // 탭 메뉴
  static const String tabHome = '홈';
  static const String tabSearch = '검색';
  static const String tabMap = '지도';
  static const String tabFavorites = '즐겨찾기';
  static const String tabProfile = '프로필';
  
  // 필터 옵션
  static const List<String> subjectFilters = [
    '전체', '수학', '영어', '과학', '외국어', '논술', '예체능', '컴퓨터', '기타'
  ];
  
  static const List<String> targetFilters = [
    '전체', '초등학생', '중학생', '고등학생', '성인'
  ];
  
  static const List<String> distanceFilters = [
    '전체', '1km 이내', '3km 이내', '5km 이내', '10km 이내'
  ];
  
  // 정렬 옵션
  static const List<String> sortOptions = [
    '관련도순', '거리순', '평점순', '리뷰순', '수강료순'
  ];
  
  // 평점
  static const double minRating = 1.0;
  static const double maxRating = 5.0;
  
  // URL
  static const String privacyPolicyUrl = 'https://academymap.co.kr/privacy';
  static const String termsOfServiceUrl = 'https://academymap.co.kr/terms';
  static const String supportEmail = 'support@academymap.co.kr';
  
  // 소셜 미디어
  static const String facebookUrl = 'https://facebook.com/academymap';
  static const String instagramUrl = 'https://instagram.com/academymap';
  static const String blogUrl = 'https://blog.academymap.co.kr';
  
  // 앱 정보
  static const String appVersion = '1.0.0';
  static const String appBuild = '1';
  
  // 개발자 모드
  static const bool isDevelopment = true;
  static const bool enableLogging = true;
  static const bool enableAnalytics = false;
}