import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:html' as html;
import 'dart:async';
import 'dart:ui_web' as ui_web;
import 'dart:math' as math;
import 'package:geolocator/geolocator.dart';
import 'academy_detail_page.dart';

class DebugLog {
  static void log(String message) {
    if (kDebugMode) {
      print(message);
    }
  }
}

void main() {
  runApp(const AcademyMapApp());
}

class AcademyMapApp extends StatelessWidget {
  const AcademyMapApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '🏫 AcademyMap',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const AcademyMapHomePage(),
    );
  }
}

class AcademyMapHomePage extends StatefulWidget {
  const AcademyMapHomePage({super.key});

  @override
  State<AcademyMapHomePage> createState() => _AcademyMapHomePageState();
}

class _AcademyMapHomePageState extends State<AcademyMapHomePage> {
  // API 설정
  static const String apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://127.0.0.1:8000');

  // 지도 범위 확장 설정
  static const double _defaultBoundsExpansion = 0.1; // ±0.1도 = 약 11km
  static const double _maxBoundsExpansion = 0.5; // ±0.5도 = 약 55km
  static const int _maxMarkersPerRequest = 200;

  // UI 상수
  static const int _scrollLoadThreshold = 200; // 스크롤 로딩 임계값 (px)
  static const int _mapInitDelay = 2000; // 지도 초기화 지연 시간 (ms)
  static const int _markerUpdateDelay = 300; // 마커 업데이트 지연 시간 (ms)
  static const double _defaultMaxPrice = 2000000.0; // 기본 최대 가격 (원)

  List<dynamic> academies = [];
  bool isLoading = false;
  List<String> selectedSubjects = ['전체']; // 다중 선택 지원
  int totalCount = 0;

  // 🚀 Cache Manager 관련 변수들
  List<dynamic> _cachedNearbyAcademies = []; // 초기 로드된 가까운 학원들 (최대 2000개)
  Map<String, List<dynamic>> _regionCache = {}; // 지역별 학원 캐시 {regionKey: academyList}
  Map<String, DateTime> _cacheTimestamps = {}; // 캐시 생성 시간 추적
  Set<String> _loadedRegions = {}; // 이미 로드된 지역들 추적
  bool _isInitialCacheLoaded = false; // 초기 캐시 로딩 완료 여부

  // 캐시 관리 설정
  static const int _maxCacheSize = 5000; // 최대 캐시 크기
  static const Duration _cacheExpireTime = Duration(minutes: 30); // 캐시 만료 시간
  static const double _regionGridSize = 0.05; // 지역 그리드 크기 (약 5km)

  // 고급 필터링 변수들
  RangeValues priceRange = const RangeValues(0.0, 2000000.0);
  List<String> selectedAgeGroups = [];
  bool shuttleFilter = false;
  bool showAdvancedFilters = false;
  bool isAndMode = false; // OR/AND 조합 모드 (false: OR, true: AND)
  
  // 무한 스크롤 변수들
  bool isLoadingMore = false;
  ScrollController scrollController = ScrollController();
  bool hasMoreData = true;
  int currentPage = 1;
  List<dynamic> allAcademyData = []; // 모든 데이터를 저장

  // 지도/리스트 토글
  bool isMapView = false;
  
  // 검색 기능
  TextEditingController searchController = TextEditingController();
  String searchQuery = '';
  Timer? searchTimer;
  
  // 위치 정보
  Position? currentPosition;
  bool isLocationLoading = false;
  bool isReturningFromDetail = false; // 상세 페이지에서 돌아온 상태

  // 오류 상태
  String? errorMessage;
  bool hasNetworkError = false;

  // 🎯 줌 레벨 관리 및 메모리 최적화 변수들
  double currentZoomLevel = 15.0; // 현재 줌 레벨
  bool isZoomedOutTooFar = false; // 50km 이상 줌아웃 상태
  bool showZoomAlert = false; // 줌 알림 모달 표시 여부
  static const double maxZoomOutDistance = 50.0; // 50km 기준
  static const double minZoomLevel = 8.0; // 50km 대응 줌 레벨 (대략적)
  Timer? zoomCheckTimer; // 줌 레벨 체크 타이머
  bool isMemoryOptimized = false; // 메모리 최적화 모드

  final List<String> subjects = [
    '전체', '수학', '영어', '과학', '외국어', '예체능', '컴퓨터', '논술', '기타', '독서실스터디카페'
  ];
  
  final List<String> ageGroups = [
    '유아', '초등', '중등', '고등', '특목고', '일반', '기타'
  ];

  @override
  void initState() {
    super.initState();
    scrollController.addListener(_onScroll);
    _setupMessageListener();
    // 위치를 먼저 가져온 다음 지도와 데이터를 초기화
    _initializeAppWithLocation();
  }

  Future<void> _initializeAppWithLocation() async {
    // 먼저 위치 정보 획득 시도
    await _getCurrentLocation();
    
    // 위치 정보를 포함하여 지도 iframe 등록
    _registerMapIframe();
    
    // 그 다음 학원 데이터 로드
    await loadAcademies();
  }

  void _registerMapIframe() {
    // 네이버 지도 iframe 등록 (위치 정보 포함)
    ui_web.platformViewRegistry.registerViewFactory(
      'naverMapIframe',
      (int viewId) {
        final iframe = html.IFrameElement()
          ..src = 'map.html'
          ..style.border = 'none'
          ..style.width = '100%'
          ..style.height = '100%';
        
        // iframe 로드 완료 후 위치 정보 전송
        iframe.onLoad.listen((_) {
          if (currentPosition != null) {
            // 지도가 완전히 초기화될 때까지 더 긴 지연시간 설정
            Future.delayed(Duration(milliseconds: _mapInitDelay), () {
              _sendLocationToMap();
              // 확실하게 하기 위해 한 번 더 전송
              Future.delayed(Duration(milliseconds: 1000), () {
                _sendLocationToMap();
              });
            });
          }
        });
        
        return iframe;
      },
    );
  }
  
  @override
  void dispose() {
    scrollController.dispose();
    searchController.dispose();
    searchTimer?.cancel();
    zoomCheckTimer?.cancel(); // 줌 체크 타이머 정리
    super.dispose();
  }
  
  void _onScroll() {
    if (scrollController.position.pixels >= scrollController.position.maxScrollExtent - _scrollLoadThreshold) {
      // 스크롤이 끝에서 200px 전에 도달하면 더 로드
      if (!isLoadingMore && hasMoreData) {
        loadMoreAcademies();
      }
    }
  }

  Future<void> _getCurrentLocation() async {
    setState(() {
      isLocationLoading = true;
    });

    try {
      // 위치 서비스 활성화 확인
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        DebugLog.log('🔍 위치 서비스가 비활성화되어 있습니다');
        setState(() {
          isLocationLoading = false;
        });
        return;
      }

      // 위치 권한 확인
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          DebugLog.log('🚫 위치 권한이 거부되었습니다');
          setState(() {
            isLocationLoading = false;
          });
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        DebugLog.log('🚫 위치 권한이 영구적으로 거부되었습니다');
        setState(() {
          isLocationLoading = false;
        });
        return;
      }

      // 현재 위치 획득
      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      setState(() {
        currentPosition = position;
        isLocationLoading = false;
      });

      DebugLog.log('📍 현재 위치 획득: ${position.latitude}, ${position.longitude}');

      // 지도가 이미 표시 중이면 위치 업데이트
      if (isMapView) {
        _sendLocationToMap();
      }

    } catch (e) {
      DebugLog.log('❌ 위치 획득 실패: $e');
      setState(() {
        isLocationLoading = false;
      });
    }
  }

  void _sendLocationToMap() {
    try {
      final iframe = html.document.querySelector('iframe') as html.IFrameElement?;
      DebugLog.log('🔍 iframe 확인: ${iframe != null}, contentWindow: ${iframe?.contentWindow != null}, currentPosition: ${currentPosition != null}');
      
      if (iframe?.contentWindow != null && currentPosition != null) {
        final message = {
          'type': 'setMapCenter',
          'lat': currentPosition!.latitude,
          'lng': currentPosition!.longitude,
        };
        DebugLog.log('📤 전송할 메시지: $message');
        
        iframe!.contentWindow!.postMessage(message, '*');
        DebugLog.log('📍 현재 위치를 지도에 전송 완료: ${currentPosition!.latitude}, ${currentPosition!.longitude}');
      } else {
        DebugLog.log('❌ iframe 또는 위치 정보가 없습니다. iframe: ${iframe != null}, position: ${currentPosition != null}');
      }
    } catch (e) {
      DebugLog.log('위치 전송 오류: $e');
    }
  }

  void _setupMessageListener() {
    // iframe에서 오는 메시지 수신
    html.window.addEventListener('message', (event) {
      final messageEvent = event as html.MessageEvent;
      if (messageEvent.data != null && messageEvent.data is Map) {
        final data = messageEvent.data as Map;
        DebugLog.log('📩 Message received - Type: ${data['type']}');
        if (data['type'] == 'requestLocation') {
          DebugLog.log('📍 지도에서 현재 위치 요청');
          _getCurrentLocation().then((_) {
            if (currentPosition != null) {
              _sendLocationToMap();
            }
          });
        } else if (data['type'] == 'requestMarkersInBounds') {
          DebugLog.log('🗺️ 지도 영역 내 마커 요청');
          final boundsData = data['data'] as Map;
          _loadMarkersInBounds(
            boundsData['sw_lat'],
            boundsData['sw_lng'], 
            boundsData['ne_lat'],
            boundsData['ne_lng'],
          );
        } else if (data['type'] == 'currentBoundsResponse') {
          DebugLog.log('🗺️ 현재 지도 영역 응답 받음');
          final boundsData = data['data'] as Map;
          _loadMarkersInBounds(
            boundsData['sw_lat'],
            boundsData['sw_lng'], 
            boundsData['ne_lat'],
            boundsData['ne_lng'],
          );
        } else if (data['type'] == 'requestClustersInBounds') {
          DebugLog.log('🏘️ 지도 영역 내 클러스터 요청');
          final boundsData = data['data'] as Map;
          _loadClustersInBounds(
            boundsData['sw_lat'],
            boundsData['sw_lng'],
            boundsData['ne_lat'],
            boundsData['ne_lng'],
          );
        } else if (data['type'] == 'mapInitialized') {
          DebugLog.log('ℹ️ 지도 초기화 완료 이벤트 수신');
          if (currentPosition != null) {
            DebugLog.log('📍 지도 초기화 완료 - 사용자 위치로 중심 이동');
            _sendLocationToMap();
          }
        } else if (data['type'] == 'zoomChanged') {
          // 🎯 줌 레벨 변경 감지
          final zoomData = data['data'] as Map;
          final newZoomLevel = (zoomData['zoom'] as num).toDouble();
          _handleZoomChange(newZoomLevel, zoomData);
        } else if (data['type'] == 'markerClicked') {
          // 📍 마커 클릭 이벤트 처리 - 상세 페이지로 네비게이션
          DebugLog.log('🎯 markerClicked 이벤트 수신됨');
          // LinkedMap을 Map<String, dynamic>으로 안전하게 변환
          final academyData = data['data'] as Map;
          final academy = Map<String, dynamic>.from(academyData);
          DebugLog.log('📍 학원 정보: ${academy['상호명'] ?? academy['name']}');
          DebugLog.log('📋 전체 데이터: $academy');
          _navigateToDetailPage(academy);
          DebugLog.log('✅ _navigateToDetailPage 호출 완료');
        }
      }
    });
  }

  // 🚀 Cache Management Methods

  /// 지역 키 생성 (그리드 기반)
  String _generateRegionKey(double lat, double lng) {
    int gridLat = (lat / _regionGridSize).round();
    int gridLng = (lng / _regionGridSize).round();
    return '${gridLat}_${gridLng}';
  }

  /// 초기 캐시에서 지역 데이터 검색
  List<dynamic> _getCachedAcademiesInBounds(double swLat, double swLng, double neLat, double neLng) {
    List<dynamic> cachedResults = [];

    // 초기 캐시에서 영역 내 학원 찾기
    for (var academy in _cachedNearbyAcademies) {
      double? lat = academy['위도'];
      double? lng = academy['경도'];

      if (lat != null && lng != null &&
          lat >= swLat && lat <= neLat &&
          lng >= swLng && lng <= neLng) {
        cachedResults.add(academy);
      }
    }

    DebugLog.log('📦 캐시에서 찾은 학원: ${cachedResults.length}개 (범위: ${swLat.toStringAsFixed(4)},${swLng.toStringAsFixed(4)} ~ ${neLat.toStringAsFixed(4)},${neLng.toStringAsFixed(4)})');
    return cachedResults;
  }

  /// 지역별 캐시에서 데이터 검색
  List<dynamic> _getRegionCachedAcademies(double swLat, double swLng, double neLat, double neLng) {
    List<dynamic> regionResults = [];
    Set<String> checkedRegions = {};

    // 해당 영역의 모든 그리드 키 생성
    double latStep = _regionGridSize;
    double lngStep = _regionGridSize;

    for (double lat = swLat; lat <= neLat; lat += latStep) {
      for (double lng = swLng; lng <= neLng; lng += lngStep) {
        String regionKey = _generateRegionKey(lat, lng);

        if (checkedRegions.contains(regionKey)) continue;
        checkedRegions.add(regionKey);

        if (_regionCache.containsKey(regionKey)) {
          // 캐시 만료 검사
          if (_cacheTimestamps[regionKey] != null &&
              DateTime.now().difference(_cacheTimestamps[regionKey]!) < _cacheExpireTime) {

            List<dynamic> regionData = _regionCache[regionKey]!;
            for (var academy in regionData) {
              double? aLat = academy['위도'];
              double? aLng = academy['경도'];

              if (aLat != null && aLng != null &&
                  aLat >= swLat && aLat <= neLat &&
                  aLng >= swLng && aLng <= neLng) {
                regionResults.add(academy);
              }
            }
          } else {
            // 만료된 캐시 제거
            _regionCache.remove(regionKey);
            _cacheTimestamps.remove(regionKey);
          }
        }
      }
    }

    DebugLog.log('🏘️ 지역 캐시에서 찾은 학원: ${regionResults.length}개');
    return regionResults;
  }

  /// 캐시에 데이터 저장
  void _cacheRegionData(double centerLat, double centerLng, List<dynamic> academies) {
    String regionKey = _generateRegionKey(centerLat, centerLng);

    // 캐시 크기 제한
    if (_regionCache.length >= 20) { // 최대 20개 지역 캐시 유지
      // 가장 오래된 캐시 제거
      String? oldestKey;
      DateTime? oldestTime;

      for (String key in _cacheTimestamps.keys) {
        DateTime? time = _cacheTimestamps[key];
        if (time != null && (oldestTime == null || time.isBefore(oldestTime))) {
          oldestTime = time;
          oldestKey = key;
        }
      }

      if (oldestKey != null) {
        _regionCache.remove(oldestKey);
        _cacheTimestamps.remove(oldestKey);
        DebugLog.log('🧹 오래된 캐시 제거: $oldestKey');
      }
    }

    _regionCache[regionKey] = List<dynamic>.from(academies);
    _cacheTimestamps[regionKey] = DateTime.now();
    DebugLog.log('💾 지역 캐시 저장: $regionKey (${academies.length}개 학원)');
  }

  /// 초기 캐시 데이터 설정
  void _setInitialCache(List<dynamic> nearbyAcademies) {
    _cachedNearbyAcademies = List<dynamic>.from(nearbyAcademies);
    _isInitialCacheLoaded = true;
    DebugLog.log('🚀 초기 캐시 설정 완료: ${_cachedNearbyAcademies.length}개 학원');
  }

  // 🎯 Zoom Level Management & Memory Optimization

  /// 줌 레벨 변경 처리
  void _handleZoomChange(double newZoomLevel, Map zoomData) {
    currentZoomLevel = newZoomLevel;

    // 50km 기준 확인 (줌 레벨 8.0 이하 = 약 50km+)
    bool wasZoomedOut = isZoomedOutTooFar;
    isZoomedOutTooFar = newZoomLevel <= minZoomLevel;

    DebugLog.log('🎯 줌 레벨 변경: ${newZoomLevel.toStringAsFixed(1)} (50km+ 여부: $isZoomedOutTooFar)');

    if (isZoomedOutTooFar && !wasZoomedOut) {
      // 50km 이상으로 줌아웃된 경우
      DebugLog.log('⚠️ 50km 이상 줌아웃 감지 - 메모리 최적화 모드 활성화');
      _activateMemoryOptimization();
      _showZoomAlertModal();
    } else if (!isZoomedOutTooFar && wasZoomedOut) {
      // 50km 이하로 줌인된 경우
      DebugLog.log('✅ 50km 이하 줌인 - 정상 모드 복귀');
      _deactivateMemoryOptimization();
      _hideZoomAlertModal();

      // 해당 영역의 마커 즉시 로드
      if (zoomData.containsKey('bounds')) {
        final bounds = zoomData['bounds'];
        _loadMarkersInBounds(
          bounds['sw_lat'],
          bounds['sw_lng'],
          bounds['ne_lat'],
          bounds['ne_lng'],
        );
      }
    }
  }

  /// 메모리 최적화 모드 활성화
  void _activateMemoryOptimization() {
    if (isMemoryOptimized) return;

    isMemoryOptimized = true;
    DebugLog.log('🔧 메모리 최적화 활성화: 클러스터 및 마커 로딩 중단');

    // 현재 표시된 마커들을 모두 제거
    _sendMarkersToMap([]);
    _sendClustersToMap([]);

    setState(() {});
  }

  /// 메모리 최적화 모드 비활성화
  void _deactivateMemoryOptimization() {
    if (!isMemoryOptimized) return;

    isMemoryOptimized = false;
    DebugLog.log('✅ 메모리 최적화 해제: 정상 로딩 재개');

    setState(() {});
  }

  /// 줌 알림 모달 표시
  void _showZoomAlertModal() {
    if (showZoomAlert) return;

    setState(() {
      showZoomAlert = true;
    });

    DebugLog.log('📢 줌 알림 모달 표시');
  }

  /// 줌 알림 모달 숨기기
  void _hideZoomAlertModal() {
    if (!showZoomAlert) return;

    setState(() {
      showZoomAlert = false;
    });

    DebugLog.log('🔽 줌 알림 모달 숨김');
  }

  /// 거리 기반 줌 레벨 계산 (대략적)
  double _calculateZoomLevelFromDistance(double distanceKm) {
    // 네이버 지도 줌 레벨 대략적 변환
    // 줌 21: ~0.01km, 줌 15: ~1km, 줌 10: ~10km, 줌 8: ~50km
    if (distanceKm <= 0.1) return 18.0;
    if (distanceKm <= 0.5) return 16.0;
    if (distanceKm <= 1.0) return 15.0;
    if (distanceKm <= 5.0) return 13.0;
    if (distanceKm <= 10.0) return 11.0;
    if (distanceKm <= 25.0) return 9.0;
    if (distanceKm <= 50.0) return 8.0;
    return 7.0; // 50km 이상
  }

  /// 🚀 Hybrid Loading: Cache-First with Progressive Enhancement
  Future<void> _loadMarkersInBounds(double swLat, double swLng, double neLat, double neLng) async {
    DebugLog.log('🗺️ 지도 영역 마커 로드 요청: (${swLat.toStringAsFixed(4)},${swLng.toStringAsFixed(4)}) ~ (${neLat.toStringAsFixed(4)},${neLng.toStringAsFixed(4)})');

    // 🎯 메모리 최적화 모드에서는 마커 로딩 중단
    if (isMemoryOptimized) {
      DebugLog.log('⛔ 메모리 최적화 모드 - 마커 로딩 중단');
      return;
    }

    // Phase 1: 캐시된 데이터로 즉시 마커 표시
    List<dynamic> cachedMarkers = [];

    // 초기 캐시에서 검색
    if (_isInitialCacheLoaded) {
      cachedMarkers.addAll(_getCachedAcademiesInBounds(swLat, swLng, neLat, neLng));
    }

    // 지역 캐시에서 추가 검색
    cachedMarkers.addAll(_getRegionCachedAcademies(swLat, swLng, neLat, neLng));

    // 중복 제거 (ID 기준)
    Map<String, dynamic> uniqueMarkers = {};
    for (var academy in cachedMarkers) {
      String id = academy['id']?.toString() ?? academy.hashCode.toString();
      uniqueMarkers[id] = academy;
    }

    List<dynamic> finalCachedMarkers = uniqueMarkers.values.toList();

    // 캐시된 마커가 있으면 즉시 표시
    if (finalCachedMarkers.isNotEmpty) {
      DebugLog.log('⚡ 캐시에서 즉시 마커 표시: ${finalCachedMarkers.length}개');
      _sendMarkersToMap(finalCachedMarkers.take(_maxMarkersPerRequest).toList());
    }

    // Phase 2: 백그라운드에서 해당 지역의 추가 데이터 로드
    try {
      // 지역 중심점 계산
      double centerLat = (swLat + neLat) / 2;
      double centerLng = (swLng + neLng) / 2;
      String regionKey = _generateRegionKey(centerLat, centerLng);

      // 이미 로드된 지역인지 확인
      bool needsApiCall = true;
      if (_loadedRegions.contains(regionKey) && _regionCache.containsKey(regionKey)) {
        // 캐시 유효성 검증
        if (_cacheTimestamps[regionKey] != null &&
            DateTime.now().difference(_cacheTimestamps[regionKey]!) < _cacheExpireTime) {
          needsApiCall = false;
          DebugLog.log('✅ 지역 캐시 유효함, API 호출 생략: $regionKey');
        }
      }

      if (needsApiCall) {
        // 사용자 위치 정보 포함하여 API 호출 (거리순 정렬을 위해)
        Map<String, String> queryParams = {
          'sw_lat': swLat.toString(),
          'sw_lng': swLng.toString(),
          'ne_lat': neLat.toString(),
          'ne_lng': neLng.toString(),
          'limit': (_maxMarkersPerRequest * 2).toString(), // 더 많은 데이터 요청
        };

        // 사용자 위치 정보 추가 (거리순 정렬)
        if (currentPosition != null) {
          queryParams['lat'] = currentPosition!.latitude.toString();
          queryParams['lon'] = currentPosition!.longitude.toString();
        }

        queryParams.addAll(getFilterParams());

        final Uri uri = Uri.parse('$apiBaseUrl/api/v1/academies/').replace(queryParameters: queryParams);
        DebugLog.log('🌐 백그라운드 API 요청: $uri');

        final response = await http.get(uri);

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          final allAcademies = data['results'] ?? [];

          // 지역 캐시에 저장
          _cacheRegionData(centerLat, centerLng, allAcademies);
          _loadedRegions.add(regionKey);

          // 범위 내 필터링
          final expandedBounds = _calculateExpandedBounds(swLat, swLng, neLat, neLng);
          final boundsAcademies = _filterAcademiesInBounds(allAcademies, expandedBounds);

          DebugLog.log('🔄 백그라운드 로드 완료: ${boundsAcademies.length}개 (API: ${allAcademies.length}개)');

          // 새로운 데이터가 캐시된 것보다 많다면 업데이트
          if (boundsAcademies.length > finalCachedMarkers.length) {
            DebugLog.log('📈 더 많은 마커 발견, 업데이트: ${boundsAcademies.length}개');
            _sendMarkersToMap(boundsAcademies.take(_maxMarkersPerRequest).toList());
          }
        } else {
          DebugLog.log('❌ API 응답 오류: ${response.statusCode}');

          // 캐시된 마커도 없다면 빈 배열 전송
          if (finalCachedMarkers.isEmpty) {
            if (response.statusCode == 429) {
              DebugLog.log('🚨 API Throttling 발생 - 잠시 후 다시 시도됩니다');
            }
            _sendMarkersToMap([]);
          }
        }
      }
    } catch (e) {
      DebugLog.log('백그라운드 마커 로드 오류: $e');

      // 에러가 발생했지만 캐시된 마커가 없다면 빈 배열 전송
      if (finalCachedMarkers.isEmpty) {
        _sendMarkersToMap([]);
      }
    }
  }

  /// 지도 범위 확장 알고리즘
  /// 줌 레벨과 Academy 밀도에 따라 동적으로 범위를 계산
  Map<String, double> _calculateExpandedBounds(double swLat, double swLng, double neLat, double neLng, {double? customExpansion}) {
    double expansion = customExpansion ?? _defaultBoundsExpansion;

    // 지도 범위의 크기에 따라 확장 비율 조정
    final latSpan = (neLat - swLat).abs();
    final lngSpan = (neLng - swLng).abs();
    final avgSpan = (latSpan + lngSpan) / 2;

    // 작은 범위일수록 더 많이 확장 (최소 가시성 보장)
    if (avgSpan < 0.01) { // 매우 작은 범위 (약 1km)
      expansion = _maxBoundsExpansion;
    } else if (avgSpan < 0.05) { // 작은 범위 (약 5km)
      expansion = _defaultBoundsExpansion * 3;
    } else if (avgSpan < 0.1) { // 중간 범위 (약 10km)
      expansion = _defaultBoundsExpansion * 2;
    }

    return {
      'swLat': swLat - expansion,
      'swLng': swLng - expansion,
      'neLat': neLat + expansion,
      'neLng': neLng + expansion,
    };
  }

  /// 지도 영역 내 학원 필터링
  List<dynamic> _filterAcademiesInBounds(List<dynamic> academies, Map<String, double> bounds) {
    return academies.where((academy) {
      final lat = academy['위도'];
      final lng = academy['경도'];

      if (lat == null || lng == null) return false;

      return lat >= bounds['swLat']! &&
             lat <= bounds['neLat']! &&
             lng >= bounds['swLng']! &&
             lng <= bounds['neLng']!;
    }).toList();
  }

  Map<String, String> getFilterParams() {
    Map<String, String> params = {};

    // 다중 과목 필터 - '전체'가 선택되지 않은 경우에만 필터 적용
    if (!selectedSubjects.contains('전체') && selectedSubjects.isNotEmpty) {
      // 다중 과목을 JSON 문자열로 전송
      params['subjects'] = jsonEncode(selectedSubjects);
      params['filterMode'] = isAndMode ? 'AND' : 'OR';
    }
    
    // 가격 범위 필터
    if (priceRange.start > 0 || priceRange.end < _defaultMaxPrice) {
      params['priceMin'] = priceRange.start.toString();
      params['priceMax'] = priceRange.end >= _defaultMaxPrice ? '999999999' : priceRange.end.toString();
    }
    
    // 연령대 필터 (Django API 호환)
    if (selectedAgeGroups.isNotEmpty) {
      for (String ageGroup in selectedAgeGroups) {
        params['age_groups'] = ageGroup;
      }
    }
    
    // 셔틀버스 필터
    if (shuttleFilter) {
      params['shuttleFilter'] = 'true';
    }
    
    // 검색어 필터
    if (searchQuery.isNotEmpty) {
      params['search'] = searchQuery;
    }
    
    return params;
  }

  Future<void> _loadClustersInBounds(double swLat, double swLng, double neLat, double neLng) async {
    // 🎯 메모리 최적화 모드에서는 클러스터 로딩 중단
    if (isMemoryOptimized) {
      DebugLog.log('⛔ 메모리 최적화 모드 - 클러스터 로딩 중단');
      return;
    }

    try {
      final Uri uri = Uri.parse('$apiBaseUrl/map_api/clusters/').replace(queryParameters: {
        'sw_lat': swLat.toString(),
        'sw_lng': swLng.toString(),
        'ne_lat': neLat.toString(),
        'ne_lng': neLng.toString(),
        ...getFilterParams(),
      });

      DebugLog.log('🏘️ 클러스터 API 요청: $uri');
      final response = await http.get(uri);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final clusters = data['clusters'] ?? [];
        
        DebugLog.log('🏘️ 지도 영역 내 클러스터: ${clusters.length}개');
        DebugLog.log('✅ 지도 영역 클러스터 업데이트: ${clusters.length}개');
        
        // iframe에 클러스터 업데이트 메시지 전송
        _sendClustersToMap(clusters);
      } else {
        DebugLog.log('❌ 클러스터 API 응답 오류: ${response.statusCode}');
        DebugLog.log('📄 응답 내용: ${response.body}');
        
        // 에러 상황에서도 빈 배열로 클러스터 클리어
        if (response.statusCode == 429) {
          DebugLog.log('🚨 클러스터 API Throttling 발생 - 잠시 후 다시 시도됩니다');
        }
        _sendClustersToMap([]);
      }
    } catch (e) {
      DebugLog.log('클러스터 로드 오류: $e');
    }
  }

  void _sendClustersToMap(List<dynamic> clustersData) {
    try {
      // iframe에 postMessage로 클러스터 데이터 전달
      final iframe = html.document.querySelector('iframe') as html.IFrameElement?;
      if (iframe?.contentWindow != null) {
        iframe!.contentWindow!.postMessage({
          'type': 'updateClusters',
          'clusters': clustersData,
        }, '*');
        DebugLog.log('✅ 지도 영역 클러스터 업데이트: ${clustersData.length}개');
      } else {
        DebugLog.log('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      DebugLog.log('클러스터 전송 오류: $e');
    }
  }

  void _sendMarkersToMap(List<dynamic> academiesData) {
    try {
      // 학원 데이터를 지도 마커로 변환
      final markersData = academiesData.map((academy) {
        return {
          'id': academy['id']?.toString() ?? academy.hashCode.toString(),
          'name': academy['상호명'] ?? '학원',
          'lat': academy['위도'],
          'lng': academy['경도'],
          'address': academy['도로명주소'] ?? '',
          'subject': _getAcademySubjects(academy),
          'primarySubject': _getPrimarySubject(academy),
          // 상세페이지를 위한 전체 데이터 포함
          ...academy,
        };
      }).where((marker) =>
        marker['lat'] != null && marker['lng'] != null
      ).toList();

      // iframe에 postMessage로 마커 데이터 전달
      final iframe = html.document.querySelector('iframe') as html.IFrameElement?;
      if (iframe?.contentWindow != null) {
        iframe!.contentWindow!.postMessage({
          'type': 'updateMarkers',
          'academies': markersData,
        }, '*');
        DebugLog.log('✅ 지도 영역 마커 업데이트: ${markersData.length}개');
      } else {
        DebugLog.log('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      DebugLog.log('지도 마커 전송 오류: $e');
    }
  }

  bool _hasActiveFilters() {
    return !selectedSubjects.contains('전체') && selectedSubjects.isNotEmpty ||
           priceRange.start > 0 ||
           priceRange.end < _defaultMaxPrice ||
           selectedAgeGroups.isNotEmpty ||
           shuttleFilter;
  }

  List<Widget> _getActiveFilterChips() {
    List<Widget> chips = [];

    // 과목 필터
    if (!selectedSubjects.contains('전체') && selectedSubjects.isNotEmpty) {
      chips.add(
        Chip(
          label: Text('📚 ${selectedSubjects.join(", ")}'),
          backgroundColor: Colors.blue[100],
          labelStyle: TextStyle(fontSize: 11, color: Colors.blue[800]),
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      );
    }

    // 가격 필터
    if (priceRange.start > 0 || priceRange.end < _defaultMaxPrice) {
      String priceText = '💰 ';
      if (priceRange.start > 0 && priceRange.end < _defaultMaxPrice) {
        priceText += '${(priceRange.start / 10000).toInt()}만~${priceRange.end >= _defaultMaxPrice ? '${(_defaultMaxPrice / 10000).toInt()}만+' : '${(priceRange.end / 10000).toInt()}만'}원';
      } else if (priceRange.start > 0) {
        priceText += '${(priceRange.start / 10000).toInt()}만원 이상';
      } else {
        priceText += '${(priceRange.end / 10000).toInt()}만원 이하';
      }
      
      chips.add(
        Chip(
          label: Text(priceText),
          backgroundColor: Colors.green[100],
          labelStyle: TextStyle(fontSize: 11, color: Colors.green[800]),
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      );
    }

    // 연령 필터
    if (selectedAgeGroups.isNotEmpty) {
      String ageText = '👶 ${selectedAgeGroups.join(', ')}';
      chips.add(
        Chip(
          label: Text(ageText),
          backgroundColor: Colors.purple[100],
          labelStyle: TextStyle(fontSize: 11, color: Colors.purple[800]),
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      );
    }

    // 셔틀버스 필터
    if (shuttleFilter) {
      chips.add(
        Chip(
          label: Text('🚌 셔틀버스'),
          backgroundColor: Colors.orange[100],
          labelStyle: TextStyle(fontSize: 11, color: Colors.orange[800]),
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      );
    }

    return chips;
  }

  void applyFiltersWithinMapBounds() {
    // iframe에 현재 지도 영역의 마커 요청 (필터가 적용된)
    final iframe = html.document.querySelector('iframe') as html.IFrameElement?;
    if (iframe?.contentWindow != null) {
      iframe!.contentWindow!.postMessage({
        'type': 'requestCurrentBounds',
      }, '*');
      DebugLog.log('🔍 현재 지도 영역에서 필터 적용 요청');
    }
  }

  Future<void> loadAcademies() async {
    if (!mounted) return;
    
    setState(() {
      isLoading = true;
      errorMessage = null;
      hasNetworkError = false;
    });

    DebugLog.log('🔍 필터링 시작: ${selectedSubjects.join(", ")} (${isAndMode ? "AND" : "OR"} 모드)'); // 디버깅용
    // 🚀 초기 로드시에는 전국 데이터 수집, 이후에는 지역 제한 적용
    final bounds = _getDynamicBounds(forceFullCountry: !_isInitialCacheLoaded);
    DebugLog.log('🌏 검색 범위: SW(${bounds['swLat']}, ${bounds['swLng']}) NE(${bounds['neLat']}, ${bounds['neLng']}) ${!_isInitialCacheLoaded ? "(전국)" : "(지역제한)"}');

    try {
      // 🚀 초기 로드 시에는 map_api에서 전체 데이터를 가져오고, 이후에는 필터링 API 사용
      late http.Response response;

      if (!_isInitialCacheLoaded) {
        // 🌍 초기 로드: 제한된 데이터 요청 (전국 범위) - 현재 필터 값 사용
        response = await http.post(
          Uri.parse('$apiBaseUrl/api/filtered_academies'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'swLat': 33.0,  // 제주도 남쪽
            'swLng': 124.0, // 한국 서쪽 경계
            'neLat': 39.0,  // 한국 북쪽 경계
            'neLng': 132.0, // 울릉도 포함 동쪽
            'subjects': selectedSubjects.isEmpty ? ['전체'] : selectedSubjects,
            'filterMode': isAndMode ? 'AND' : 'OR',
            'priceMin': priceRange.start.toString(),
            'priceMax': priceRange.end >= _defaultMaxPrice ? '999999999' : priceRange.end.toString(),
            'ageGroups': selectedAgeGroups,
            'shuttleFilter': shuttleFilter,
            'searchQuery': searchQuery.trim(),
            'limit': 1000,  // 초기 로드 시 데이터 제한
            // 📍 사용자 위치 정보 추가 (거리순 정렬을 위해)
            'userLat': currentPosition?.latitude ?? 37.5665,
            'userLng': currentPosition?.longitude ?? 126.9780,
          }),
        );
        DebugLog.log('🚀 초기 데이터 로드 요청: 최대 1000개, 필터: ${selectedSubjects.join(", ")}, 가격: ${priceRange.start}-${priceRange.end}');
      } else {
        // 🔍 이후 필터링: 기존 방식 사용
        response = await http.post(
          Uri.parse('$apiBaseUrl/api/filtered_academies'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'swLat': bounds['swLat'],
            'swLng': bounds['swLng'],
            'neLat': bounds['neLat'],
            'neLng': bounds['neLng'],
            'subjects': selectedSubjects,
            'priceMin': priceRange.start.toString(),
            'priceMax': priceRange.end >= _defaultMaxPrice ? '999999999' : priceRange.end.toString(),
            'filterMode': isAndMode ? 'AND' : 'OR',
            'ageGroups': selectedAgeGroups,
            'shuttleFilter': shuttleFilter,
            'searchQuery': searchQuery.trim(),
            // 📍 사용자 위치 정보 추가 (거리순 정렬을 위해)
            'userLat': currentPosition?.latitude,
            'userLng': currentPosition?.longitude,
          }),
        );
      }

      DebugLog.log('📡 API 응답 코드: ${response.statusCode}'); // 디버깅용

      if (response.statusCode == 200) {
        final String responseBody = utf8.decode(response.bodyBytes);
        DebugLog.log('🔍 원시 응답 길이: ${responseBody.length}');
        DebugLog.log('🔍 원시 응답 샘플: ${responseBody.substring(0, math.min(200, responseBody.length))}...');

        // 🌍 초기 로드와 이후 필터링 모두 동일한 형식으로 처리
        final List<dynamic> data = json.decode(responseBody);

        if (!_isInitialCacheLoaded) {
          DebugLog.log('📊 받은 전체 데이터 수: ${data.length}개 (98,651개 중)');
        } else {
          DebugLog.log('📊 받은 필터링 데이터 수: ${data.length}개');
        }

        // 받은 데이터의 ID 목록 로깅
        final ids = data.map((item) => item['id']).toList();
        DebugLog.log('🔍 받은 학원 ID: $ids');
        
        if (!mounted) return;
        setState(() {
          // 첫 로드시 데이터 초기화
          allAcademyData = data;
          academies = data.take(50).toList(); // 처음 50개만 표시
          totalCount = data.length;
          currentPage = 1;
          hasMoreData = data.length > 50;
          isLoading = false;
        });

        // 🚀 초기 캐시 설정 (거리순으로 정렬된 가까운 학원들)
        if (!_isInitialCacheLoaded) {
          _setInitialCache(data);
        }

        DebugLog.log('✅ UI 업데이트 완료: ${academies.length}개 표시'); // 디버깅용
        
        // 지도가 활성화되어 있으면 마커 업데이트
        if (isMapView) {
          Future.delayed(Duration(milliseconds: _markerUpdateDelay), () {
            _addAcademyMarkersToMap();
          });
        }
      } else {
        throw Exception('서버 오류: ${response.statusCode}');
      }
    } catch (e) {
      DebugLog.log('❌ 오류 발생: $e'); // 디버깅용
      if (!mounted) return;

      setState(() {
        isLoading = false;
        hasNetworkError = true;

        if (e.toString().contains('SocketException') ||
            e.toString().contains('TimeoutException') ||
            e.toString().contains('ClientException')) {
          errorMessage = '네트워크 연결을 확인해주세요';
        } else if (e.toString().contains('404')) {
          errorMessage = '서비스를 찾을 수 없습니다';
        } else if (e.toString().contains('500')) {
          errorMessage = '서버에 일시적인 문제가 발생했습니다';
        } else {
          errorMessage = '데이터를 불러오는 중 오류가 발생했습니다';
        }
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                Icon(Icons.error_outline, color: Colors.white),
                SizedBox(width: 8),
                Expanded(child: Text(errorMessage!)),
              ],
            ),
            backgroundColor: Colors.red,
            action: SnackBarAction(
              label: '재시도',
              textColor: Colors.white,
              onPressed: () => loadAcademies(),
            ),
            duration: Duration(seconds: 5),
          ),
        );
      }
    }
  }

  Future<void> loadMoreAcademies() async {
    if (isLoadingMore || !hasMoreData) return;
    
    setState(() {
      isLoadingMore = true;
    });

    try {
      // 현재 페이지의 다음 50개 데이터를 로드
      int startIndex = currentPage * 50;
      int endIndex = (startIndex + 50).clamp(0, allAcademyData.length);
      
      if (startIndex >= allAcademyData.length) {
        setState(() {
          hasMoreData = false;
          isLoadingMore = false;
        });
        return;
      }
      
      List<dynamic> newAcademies = allAcademyData.sublist(startIndex, endIndex);
      
      await Future.delayed(Duration(milliseconds: 500)); // 로딩 효과
      
      if (!mounted) return;
      setState(() {
        academies.addAll(newAcademies);
        currentPage++;
        hasMoreData = endIndex < allAcademyData.length;
        isLoadingMore = false;
      });
      
      DebugLog.log('📄 페이지 $currentPage 로드: ${newAcademies.length}개 추가 (총 ${academies.length}개)');
      
    } catch (e) {
      DebugLog.log('❌ 추가 로딩 오류: $e');
      if (!mounted) return;
      setState(() {
        isLoadingMore = false;
      });
    }
  }

  void _showAcademyDetail(Map<String, dynamic> academy) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        child: Container(
          padding: const EdgeInsets.all(20),
          constraints: const BoxConstraints(maxWidth: 400, maxHeight: 600),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 제목
              Row(
                children: [
                  Expanded(
                    child: Text(
                      academy['상호명'] ?? '학원 정보',
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              
              // 상세 정보
              Flexible(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInfoRow('📍', '주소', academy['도로명주소']),
                      _buildInfoRow('📞', '전화', academy['전화번호']),
                      _buildInfoRow('⭐', '평점', academy['별점']?.toString()),
                      _buildInfoRow('💰', '수강료', academy['수강료_평균']?.toString()),
                      _buildInfoRow('🕒', '영업시간', academy['영업시간']),
                      _buildInfoRow('🚌', '셔틀버스', academy['셔틀버스'] == 'true' ? '운행' : '미운행'),
                      
                      const SizedBox(height: 16),
                      
                      // 대상 연령
                      const Text(
                        '👶 대상 연령',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        children: [
                          if (academy['대상_유아'] == true) _buildChip('유아', Colors.pink),
                          if (academy['대상_초등'] == true) _buildChip('초등', Colors.blue),
                          if (academy['대상_중등'] == true) _buildChip('중등', Colors.green),
                          if (academy['대상_고등'] == true) _buildChip('고등', Colors.orange),
                          if (academy['대상_특목고'] == true) _buildChip('특목고', Colors.purple),
                          if (academy['대상_일반'] == true) _buildChip('일반', Colors.grey),
                          if (academy['대상_기타'] == true) _buildChip('기타', Colors.brown),
                        ],
                      ),
                      
                      const SizedBox(height: 16),
                      
                      // 과목 정보
                      const Text(
                        '📚 과목',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        children: [
                          if (academy['과목_수학'] == true) _buildChip('수학', Colors.red),
                          if (academy['과목_영어'] == true) _buildChip('영어', Colors.blue),
                          if (academy['과목_과학'] == true) _buildChip('과학', Colors.green),
                          if (academy['과목_외국어'] == true) _buildChip('외국어', Colors.purple),
                          if (academy['과목_예체능'] == true) _buildChip('예체능', Colors.orange),
                          if (academy['과목_컴퓨터'] == true) _buildChip('컴퓨터', Colors.cyan),
                          if (academy['과목_논술'] == true) _buildChip('논술', Colors.brown),
                          if (academy['과목_기타'] == true) _buildChip('기타', Colors.grey),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 16),
              
              // 액션 버튼들
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        final lat = academy['위도'];
                        final lng = academy['경도'];
                        if (lat != null && lng != null) {
                          final url = 'https://map.naver.com/v5/search/${Uri.encodeComponent(academy['상호명'] ?? '')}';
                          html.window.open(url, '_blank');
                        }
                      },
                      icon: Icon(Icons.navigation, size: 18),
                      label: Text('길찾기'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        final phone = academy['전화번호'];
                        if (phone != null && phone.isNotEmpty && phone != 'null') {
                          final phoneUrl = 'tel:${phone.replaceAll('-', '')}';
                          html.window.open(phoneUrl, '_self');
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('전화번호가 없습니다')),
                          );
                        }
                      },
                      icon: Icon(Icons.phone, size: 18),
                      label: Text('전화'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              
              SizedBox(height: 8),
              
              // 닫기 버튼
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.grey[300],
                    foregroundColor: Colors.grey[700],
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text('닫기'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String icon, String label, String? value) {
    if (value == null || value.isEmpty || value == 'null' || value == 'false') {
      return const SizedBox.shrink();
    }
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(icon, style: const TextStyle(fontSize: 16)),
          const SizedBox(width: 8),
          Text(
            '$label: ',
            style: const TextStyle(
              fontWeight: FontWeight.w500,
              fontSize: 14,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChip(String label, Color color) {
    return Chip(
      label: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          color: Colors.white,
        ),
      ),
      backgroundColor: color.withOpacity(0.8),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  // 학원 상세 페이지로 네비게이션
  Future<void> _navigateToDetailPage(Map<String, dynamic> academy) async {
    DebugLog.log('🚀 _navigateToDetailPage 함수 시작');
    DebugLog.log('📱 학원명: ${academy['상호명'] ?? 'Unknown'}');
    try {
      final result = await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => AcademyDetailPage(academy: academy),
        ),
      );
      DebugLog.log('✅ Navigator.push 성공');

      // 상세 페이지에서 지도보기를 눌러 돌아온 경우
      if (result != null && result is Map) {
        final lat = result['lat'];
        final lng = result['lng'];
        final name = result['name'];

        DebugLog.log('📍 상세 페이지에서 지도 위치 요청: $name ($lat, $lng)');

        // 상세 페이지에서 돌아온 상태 설정
        setState(() {
          isReturningFromDetail = true;
        });

        // 리스트 뷰인 경우 지도 뷰로 전환
        if (!isMapView) {
          DebugLog.log('🔄 리스트 뷰에서 지도 뷰로 전환');
          setState(() {
            isMapView = true;
          });

          // 지도가 로드될 때까지 잠시 대기
          Future.delayed(Duration(milliseconds: 500), () {
            _centerMapOnAcademy(lat, lng);
          });
        } else {
          // 이미 지도 뷰인 경우 바로 이동
          _centerMapOnAcademy(lat, lng);
        }

        // 3초 후에 플래그 해제
        Future.delayed(Duration(seconds: 3), () {
          if (mounted) {
            setState(() {
              isReturningFromDetail = false;
            });
          }
        });
      }
    } catch (e) {
      DebugLog.log('❌ Navigation 오류: $e');
    }
  }

  // 지도를 특정 학원 위치로 중심 이동
  void _centerMapOnAcademy(double lat, double lng) {
    try {
      final iframe = html.document.querySelector('iframe') as html.IFrameElement?;

      if (iframe?.contentWindow != null) {
        final message = {
          'type': 'setMapCenter',
          'lat': lat,
          'lng': lng,
        };

        iframe!.contentWindow!.postMessage(message, '*');
        DebugLog.log('📍 학원 위치로 지도 중심 이동: $lat, $lng');
      } else {
        DebugLog.log('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      DebugLog.log('❌ 지도 중심 이동 오류: $e');
    }
  }

  Widget _buildNaverMapWidget() {
    return Container(
      height: double.infinity,
      child: Stack(
        children: [
          // iframe으로 네이버 지도 표시
          HtmlElementView(
            viewType: 'naverMapIframe',
            onPlatformViewCreated: (int viewId) {
              Future.delayed(Duration(milliseconds: 1000), () {
                _addAcademyMarkersToMap();
              });
            },
          ),
          // 로딩 인디케이터
          if (isLoading)
            Container(
              color: Colors.white.withOpacity(0.8),
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('지도를 로딩하는 중...'),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }


  void _addAcademyMarkersToMap() {
    if (academies.isEmpty) return;

    // 학원 데이터를 지도 마커로 변환
    final markersData = academies.map((academy) {
      return {
        'id': academy['id']?.toString() ?? academy.hashCode.toString(),
        'name': academy['상호명'] ?? '학원',
        'lat': academy['위도'],
        'lng': academy['경도'],
        'address': academy['도로명주소'] ?? '',
        'subject': _getAcademySubjects(academy),
        'primarySubject': _getPrimarySubject(academy), // 주요 과목 추가
        // 상세페이지를 위한 전체 데이터 포함
        ...academy,
      };
    }).where((marker) =>
      marker['lat'] != null && marker['lng'] != null
    ).toList();

    try {
      // iframe에 postMessage로 마커 데이터 전달
      final iframe = html.document.querySelector('iframe') as html.IFrameElement?;
      if (iframe?.contentWindow != null) {
        iframe!.contentWindow!.postMessage({
          'type': 'updateMarkers',
          'academies': markersData,
        }, '*');
        DebugLog.log('✅ iframe에 ${markersData.length}개 마커 데이터 전송');
      } else {
        DebugLog.log('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      DebugLog.log('마커 업데이트 오류: $e');
    }
  }

  String _getAcademySubjects(Map<String, dynamic> academy) {
    List<String> subjects = [];
    if (academy['과목_수학'] == true) subjects.add('수학');
    if (academy['과목_영어'] == true) subjects.add('영어');
    if (academy['과목_과학'] == true) subjects.add('과학');
    if (academy['과목_외국어'] == true) subjects.add('외국어');
    if (academy['과목_예체능'] == true) subjects.add('예체능');
    if (academy['과목_컴퓨터'] == true) subjects.add('컴퓨터');
    if (academy['과목_논술'] == true) subjects.add('논술');
    if (academy['과목_기타'] == true) subjects.add('기타');
    return subjects.join(', ');
  }

  // 학원의 주요 과목을 판단 (첫 번째 과목 또는 우선순위)
  String _getPrimarySubject(Map<String, dynamic> academy) {
    if (academy['과목_수학'] == true) return '수학';
    if (academy['과목_영어'] == true) return '영어';
    if (academy['과목_과학'] == true) return '과학';
    if (academy['과목_예체능'] == true) return '예체능';
    if (academy['과목_컴퓨터'] == true) return '컴퓨터';
    if (academy['과목_외국어'] == true) return '외국어';
    if (academy['과목_논술'] == true) return '논술';
    if (academy['과목_기타'] == true) return '기타';
    return '기타'; // 과목 정보가 없는 경우
  }

  // 과목별 색상 반환
  Color _getSubjectColor(String subject) {
    switch (subject) {
      case '수학': return const Color(0xFFDC3545);
      case '영어': return const Color(0xFF007BFF);
      case '과학': return const Color(0xFF28A745);
      case '예체능': return const Color(0xFFFD7E14);
      case '컴퓨터': return const Color(0xFF17A2B8);
      case '외국어': return const Color(0xFF6F42C1);
      case '논술': return const Color(0xFF795548);
      default: return const Color(0xFF6C757D);
    }
  }

  // 과목별 아이콘 반환
  String _getSubjectIcon(String subject) {
    switch (subject) {
      case '수학': return '➕';
      case '영어': return '📚';
      case '과학': return '🔬';
      case '예체능': return '🎨';
      case '컴퓨터': return '💻';
      case '외국어': return '🌍';
      case '논술': return '✏️';
      default: return '📖';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Container(
          height: 40,
          child: TextField(
            controller: searchController,
            decoration: InputDecoration(
              hintText: '학원명/지역 검색',
              prefixIcon: Icon(Icons.search, color: Colors.grey[600], size: 20),
              suffixIcon: searchQuery.isNotEmpty 
                ? IconButton(
                    icon: Icon(Icons.clear, size: 18),
                    onPressed: () {
                      searchController.clear();
                      setState(() {
                        searchQuery = '';
                      });
                      loadAcademies();
                    },
                  )
                : null,
              filled: true,
              fillColor: Colors.white.withOpacity(0.9),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(20),
                borderSide: BorderSide.none,
              ),
              contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              hintStyle: TextStyle(
                color: Colors.grey[600],
                fontSize: 14,
              ),
            ),
            style: TextStyle(fontSize: 14),
            onChanged: (value) {
              setState(() {
                searchQuery = value;
              });
              
              // 검색 debouncing - 500ms 후에 검색 실행
              searchTimer?.cancel();
              searchTimer = Timer(Duration(milliseconds: 500), () {
                if (mounted) {
                  loadAcademies();
                }
              });
            },
            onSubmitted: (value) {
              loadAcademies();
            },
          ),
        ),
        elevation: 2,
        actions: [
          Container(
            margin: EdgeInsets.only(right: 8),
            child: ToggleButtons(
              borderRadius: BorderRadius.circular(20),
              constraints: BoxConstraints(minWidth: 40, minHeight: 36),
              isSelected: [!isMapView, isMapView],
              onPressed: (int index) {
                setState(() {
                  isMapView = index == 1;
                });
                if (isMapView) {
                  // 지도 뷰로 전환할 때 위치 및 마커 업데이트
                  Future.delayed(Duration(milliseconds: 500), () {
                    // 상세 페이지에서 돌아온 경우가 아닐 때만 사용자 위치로 이동
                    if (!isReturningFromDetail) {
                      _sendLocationToMap();
                    }
                    _addAcademyMarkersToMap();
                  });
                }
              },
              children: [
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.list, size: 18),
                      SizedBox(width: 4),
                      Text('리스트', style: TextStyle(fontSize: 12)),
                    ],
                  ),
                ),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.map, size: 18),
                      SizedBox(width: 4),
                      Text('지도', style: TextStyle(fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(showAdvancedFilters ? Icons.filter_list : Icons.tune),
            tooltip: '고급 필터',
            onPressed: () {
              setState(() {
                showAdvancedFilters = !showAdvancedFilters;
              });
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              // 필터 섹션
              Container(
            padding: EdgeInsets.all(MediaQuery.of(context).size.width > 600 ? 16.0 : 12.0),
            decoration: BoxDecoration(
              color: Colors.grey[50],
              border: Border(
                bottom: BorderSide(color: Colors.grey[300]!),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '📚 과목 선택',
                      style: TextStyle(
                        fontSize: MediaQuery.of(context).size.width > 600 ? 16 : 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    TextButton.icon(
                      onPressed: _hasActiveFilters() ? () {
                        setState(() {
                          selectedSubjects = ['전체'];
                          priceRange = const RangeValues(0.0, 2000000.0);
                          selectedAgeGroups.clear();
                          shuttleFilter = false;
                        });
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('🔄 필터가 초기화되었습니다'),
                            duration: Duration(seconds: 2),
                          ),
                        );
                        Future.delayed(Duration(milliseconds: _markerUpdateDelay), () {
                          loadAcademies();  // 리스트와 맵 모두 업데이트
                        });
                      } : null,
                      icon: Icon(
                        Icons.refresh, 
                        size: 18,
                        color: _hasActiveFilters() ? Colors.blue[700] : Colors.grey[400],
                      ),
                      label: Text(
                        '초기화',
                        style: TextStyle(
                          fontSize: 12,
                          color: _hasActiveFilters() ? Colors.blue[700] : Colors.grey[400],
                        ),
                      ),
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        minimumSize: Size(0, 0),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: MediaQuery.of(context).size.width > 600 ? 8.0 : 6.0,
                  runSpacing: 4.0,
                  children: subjects.map((subject) {
                    bool isSelected = selectedSubjects.contains(subject);
                    return FilterChip(
                      label: Text(subject),
                      selected: isSelected,
                      onSelected: (bool selected) {
                        setState(() {
                          if (subject == '전체') {
                            // '전체' 선택 시 다른 모든 선택 해제
                            if (selected) {
                              selectedSubjects = ['전체'];
                            } else {
                              selectedSubjects = [];
                            }
                          } else {
                            // 개별 과목 선택/해제
                            if (selected) {
                              // '전체' 선택되어 있으면 제거하고 새 과목 추가
                              selectedSubjects.remove('전체');
                              if (!selectedSubjects.contains(subject)) {
                                selectedSubjects.add(subject);
                              }
                            } else {
                              selectedSubjects.remove(subject);
                              // 아무것도 선택되지 않았으면 '전체' 자동 선택
                              if (selectedSubjects.isEmpty) {
                                selectedSubjects.add('전체');
                              }
                            }
                          }
                        });

                        DebugLog.log('🎯 과목 선택: ${selectedSubjects.join(", ")}'); // 디버깅용

                        // UI 업데이트 후 필터 적용
                        Future.delayed(Duration(milliseconds: 100), () {
                          loadAcademies();  // 리스트와 맵 모두 업데이트
                        });
                      },
                      selectedColor: Colors.blue[100],
                      checkmarkColor: Colors.blue[800],
                    );
                  }).toList(),
                ),

                // OR/AND 조합 모드 토글 (다중 선택 시만 표시)
                if (!selectedSubjects.contains('전체') && selectedSubjects.length > 1) ...[
                  const SizedBox(height: 8),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        '필터 모드: ',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[700],
                        ),
                      ),
                      Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          color: Colors.grey[100],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            GestureDetector(
                              onTap: () {
                                if (isAndMode) {
                                  setState(() {
                                    isAndMode = false;
                                  });
                                  loadAcademies();  // 리스트와 맵 모두 업데이트
                                }
                              },
                              child: Container(
                                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(16),
                                  color: !isAndMode ? Colors.blue : Colors.transparent,
                                ),
                                child: Text(
                                  'OR',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: !isAndMode ? Colors.white : Colors.grey[600],
                                    fontWeight: !isAndMode ? FontWeight.bold : FontWeight.normal,
                                  ),
                                ),
                              ),
                            ),
                            GestureDetector(
                              onTap: () {
                                if (!isAndMode) {
                                  setState(() {
                                    isAndMode = true;
                                  });
                                  loadAcademies();  // 리스트와 맵 모두 업데이트
                                }
                              },
                              child: Container(
                                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(16),
                                  color: isAndMode ? Colors.blue : Colors.transparent,
                                ),
                                child: Text(
                                  'AND',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: isAndMode ? Colors.white : Colors.grey[600],
                                    fontWeight: isAndMode ? FontWeight.bold : FontWeight.normal,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        isAndMode ? '모든 과목 동시 제공' : '선택 과목 중 하나 이상',
                        style: TextStyle(
                          fontSize: 10,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ],

                if (totalCount > 0) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.blue[50],
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '📊 "${selectedSubjects.join(", ")}" 학원 $totalCount개 중 ${academies.length}개 표시${hasMoreData ? ' (스크롤하여 더 보기)' : ''}',
                      style: TextStyle(
                        color: Colors.blue[700],
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
                
                // 활성 필터 상태 표시
                if (_hasActiveFilters()) ...[
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.orange[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.orange[200]!),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.filter_alt, size: 16, color: Colors.orange[700]),
                            const SizedBox(width: 4),
                            Text(
                              '활성 필터',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: Colors.orange[700],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          runSpacing: 4,
                          children: _getActiveFilterChips(),
                        ),
                      ],
                    ),
                  ),
                ],
                
                // 고급 필터 섹션
                if (showAdvancedFilters) ...[
                  const SizedBox(height: 16),
                  const Divider(),
                  
                  // 가격 필터
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '💰 수강료',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${priceRange.start.toInt().toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (Match m) => '${m[1]},')}원 - ${priceRange.end >= _defaultMaxPrice ? '${(_defaultMaxPrice / 10000).toInt()}만원 이상' : '${priceRange.end.toInt().toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (Match m) => '${m[1]},')}원'}',
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 14,
                        ),
                      ),
                      RangeSlider(
                        values: priceRange,
                        min: 0,
                        max: _defaultMaxPrice.toDouble(),
                        divisions: 20,
                        labels: RangeLabels(
                          '${(priceRange.start / 10000).toInt()}만원',
                          priceRange.end >= _defaultMaxPrice ? '${(_defaultMaxPrice / 10000).toInt()}만원+' : '${(priceRange.end / 10000).toInt()}만원',
                        ),
                        onChanged: (RangeValues values) {
                          setState(() {
                            priceRange = values;
                          });
                        },
                        onChangeEnd: (RangeValues values) {
                          Future.delayed(Duration(milliseconds: _markerUpdateDelay), () {
                            loadAcademies();  // 리스트와 맵 모두 업데이트
                          });
                        },
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // 연령 필터
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '👶 연령',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8.0,
                        children: ageGroups.map((age) {
                          return FilterChip(
                            label: Text(age),
                            selected: selectedAgeGroups.contains(age),
                            onSelected: (bool selected) {
                              setState(() {
                                if (selected) {
                                  selectedAgeGroups.add(age);
                                } else {
                                  selectedAgeGroups.remove(age);
                                }
                              });
                              Future.delayed(Duration(milliseconds: 200), () {
                                loadAcademies();  // 리스트와 맵 모두 업데이트
                              });
                            },
                            selectedColor: Colors.green[100],
                            checkmarkColor: Colors.green[800],
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // 셔틀버스 필터
                  Row(
                    children: [
                      const Text(
                        '🚌 셔틀버스',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Spacer(),
                      Switch(
                        value: shuttleFilter,
                        onChanged: (bool value) {
                          setState(() {
                            shuttleFilter = value;
                          });
                          Future.delayed(Duration(milliseconds: 200), () {
                            loadAcademies();  // 리스트와 맵 모두 업데이트
                          });
                        },
                        activeColor: Colors.green,
                      ),
                    ],
                  ),
                ],
                  ],
                ),
              ),
              // 학원 목록 또는 지도
              Expanded(
                child: isMapView
              ? _buildNaverMapWidget()
              : isLoading
                  ? Center(
                      child: Container(
                        padding: EdgeInsets.all(32),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              padding: EdgeInsets.all(20),
                              decoration: BoxDecoration(
                                color: Colors.blue[50],
                                shape: BoxShape.circle,
                              ),
                              child: CircularProgressIndicator(
                                strokeWidth: 3,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.blue[600]!),
                              ),
                            ),
                            const SizedBox(height: 20),
                            Text(
                              '🔍 학원 정보를 불러오는 중...',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                                color: Colors.grey[700],
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '잠시만 기다려주세요',
                              style: TextStyle(
                                fontSize: 14,
                                color: Colors.grey[500],
                              ),
                            ),
                            if (_hasActiveFilters()) ...[
                              const SizedBox(height: 16),
                              Container(
                                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                decoration: BoxDecoration(
                                  color: Colors.orange[50],
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: Colors.orange[200]!),
                                ),
                                child: Text(
                                  '필터가 적용된 결과를 찾는 중',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.orange[700],
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    )
                  : academies.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                hasNetworkError ? Icons.wifi_off : Icons.school_outlined,
                                size: 64,
                                color: hasNetworkError ? Colors.red : Colors.grey,
                              ),
                              SizedBox(height: 16),
                              Text(
                                hasNetworkError
                                  ? (errorMessage ?? '연결 오류가 발생했습니다')
                                  : '조건에 맞는 학원이 없습니다',
                                style: TextStyle(
                                  fontSize: 18,
                                  color: hasNetworkError ? Colors.red : Colors.grey,
                                ),
                                textAlign: TextAlign.center,
                              ),
                              if (hasNetworkError) ...[
                                SizedBox(height: 16),
                                ElevatedButton.icon(
                                  onPressed: loadAcademies,
                                  icon: Icon(Icons.refresh),
                                  label: Text('다시 시도'),
                                ),
                              ],
                            ],
                          ),
                        )
                    : RefreshIndicator(
                        onRefresh: loadAcademies,
                        child: ListView.builder(
                          controller: scrollController,
                          itemCount: academies.length + (isLoadingMore ? 1 : (hasMoreData ? 1 : 0)),
                          itemBuilder: (context, index) {
                            // 로딩 인디케이터 표시
                            if (index == academies.length) {
                              if (isLoadingMore) {
                                return Container(
                                  padding: const EdgeInsets.all(20),
                                  child: Center(
                                    child: Container(
                                      padding: EdgeInsets.all(16),
                                      decoration: BoxDecoration(
                                        color: Colors.grey[50],
                                        borderRadius: BorderRadius.circular(12),
                                        border: Border.all(color: Colors.grey[200]!),
                                      ),
                                      child: Column(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          SizedBox(
                                            width: 24,
                                            height: 24,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              valueColor: AlwaysStoppedAnimation<Color>(Colors.blue[600]!),
                                            ),
                                          ),
                                          const SizedBox(height: 12),
                                          Text(
                                            '📚 더 많은 학원을 찾는 중...',
                                            style: TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.w500,
                                              color: Colors.grey[700],
                                            ),
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            '스크롤을 계속해보세요',
                                            style: TextStyle(
                                              fontSize: 12,
                                              color: Colors.grey[500],
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                );
                              } else if (hasMoreData) {
                                return Container(
                                  padding: const EdgeInsets.all(16),
                                  child: Center(
                                    child: TextButton(
                                      onPressed: loadMoreAcademies,
                                      child: const Text('더 보기'),
                                    ),
                                  ),
                                );
                              } else {
                                return Container(
                                  padding: const EdgeInsets.all(16),
                                  child: Center(
                                    child: Text(
                                      '모든 학원 정보를 표시했습니다 (총 ${academies.length}개)',
                                      style: TextStyle(
                                        color: Colors.grey[600],
                                        fontSize: 14,
                                      ),
                                    ),
                                  ),
                                );
                              }
                            }
                            final academy = academies[index];
                            return Card(
                              margin: const EdgeInsets.symmetric(
                                horizontal: 16.0,
                                vertical: 4.0,
                              ),
                              child: ListTile(
                                leading: Container(
                                  width: 60,
                                  height: 60,
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: academy['학원사진'] != null &&
                                           academy['학원사진'] != '' &&
                                           academy['학원사진'] != 'null'
                                      ? Image.network(
                                          academy['학원사진'],
                                          fit: BoxFit.cover,
                                          errorBuilder: (context, error, stackTrace) {
                                            // 이미지 로드 실패 시 기본 아이콘 표시
                                            return Container(
                                              decoration: BoxDecoration(
                                                color: _getSubjectColor(_getPrimarySubject(academy)),
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: Center(
                                                child: Text(
                                                  _getSubjectIcon(_getPrimarySubject(academy)),
                                                  style: const TextStyle(fontSize: 24),
                                                ),
                                              ),
                                            );
                                          },
                                          loadingBuilder: (context, child, loadingProgress) {
                                            if (loadingProgress == null) return child;
                                            return Container(
                                              decoration: BoxDecoration(
                                                color: Colors.grey[200],
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: Center(
                                                child: CircularProgressIndicator(
                                                  value: loadingProgress.expectedTotalBytes != null
                                                      ? loadingProgress.cumulativeBytesLoaded /
                                                          loadingProgress.expectedTotalBytes!
                                                      : null,
                                                  strokeWidth: 2,
                                                ),
                                              ),
                                            );
                                          },
                                        )
                                      : Container(
                                          decoration: BoxDecoration(
                                            color: _getSubjectColor(_getPrimarySubject(academy)),
                                            borderRadius: BorderRadius.circular(8),
                                          ),
                                          child: Center(
                                            child: Text(
                                              _getSubjectIcon(_getPrimarySubject(academy)),
                                              style: const TextStyle(fontSize: 24),
                                            ),
                                          ),
                                        ),
                                  ),
                                ),
                                title: InkWell(
                                  onTap: () {
                                    _navigateToDetailPage(academy);
                                  },
                                  child: Text(
                                    academy['상호명'] ?? '이름 없음',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blue,
                                      decoration: TextDecoration.underline,
                                    ),
                                  ),
                                ),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      academy['도로명주소'] ?? '주소 없음',
                                      style: TextStyle(
                                        color: Colors.grey[600],
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Row(
                                      children: [
                                        // 📍 거리 정보 표시 (우선 순위)
                                        if (academy['distance'] != null && _formatDistance(academy['distance']).isNotEmpty) ...[
                                          Icon(
                                            Icons.near_me,
                                            size: 16,
                                            color: Colors.blue[600],
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            _formatDistance(academy['distance']),
                                            style: TextStyle(
                                              fontSize: 12,
                                              color: Colors.blue[700],
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          const SizedBox(width: 12),
                                        ],
                                        // 기존 위치 정보 (축약)
                                        Icon(
                                          Icons.location_on,
                                          size: 16,
                                          color: Colors.grey[400],
                                        ),
                                        const SizedBox(width: 4),
                                        Expanded(
                                          child: Text(
                                            '${_safeSubstring(academy['위도']?.toString(), 7)}, ${_safeSubstring(academy['경도']?.toString(), 8)}',
                                            style: TextStyle(
                                              fontSize: 11,
                                              color: Colors.grey[500],
                                            ),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                                trailing: Icon(
                                  Icons.arrow_forward_ios,
                                  size: 16,
                                  color: Colors.grey[400],
                                ),
                                onTap: () {
                                  _navigateToDetailPage(academy);
                                },
                              ),
                            );
                          },
                        ),
                      ),
              ),
            ],
          ),
          // 🎯 반투명 줌 알림 모달
          if (showZoomAlert)
            Container(
              color: Colors.black.withOpacity(0.3), // 반투명 배경
              child: Center(
                child: Container(
                  margin: EdgeInsets.all(40),
                  padding: EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        spreadRadius: 2,
                        blurRadius: 8,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // 아이콘
                      Container(
                        width: 60,
                        height: 60,
                        decoration: BoxDecoration(
                          color: Colors.orange[100],
                          borderRadius: BorderRadius.circular(30),
                        ),
                        child: Icon(
                          Icons.zoom_out_map,
                          size: 32,
                          color: Colors.orange[700],
                        ),
                      ),
                      SizedBox(height: 16),

                      // 제목
                      Text(
                        '지도를 확대해주세요',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Colors.grey[800],
                        ),
                      ),
                      SizedBox(height: 12),

                      // 설명
                      Text(
                        '현재 너무 멀리서 보고 있어요.\n메모리 절약을 위해 마커 표시를\n일시 중단했습니다.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[600],
                          height: 1.4,
                        ),
                      ),
                      SizedBox(height: 20),

                      // 확인 버튼 (사실상 데코레이션)
                      Container(
                        width: double.infinity,
                        padding: EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: Colors.blue,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '지도를 확대하면 자동으로 마커가 표시됩니다',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ), // body: Stack 끝
    );
  }

  // 안전한 substring 처리를 위한 헬퍼 함수
  String _safeSubstring(String? str, int maxLength) {
    if (str == null || str.isEmpty) return 'N/A';
    return str.length <= maxLength ? str : str.substring(0, maxLength);
  }

  // 📍 거리 포맷 함수
  String _formatDistance(dynamic distanceValue) {
    if (distanceValue == null) return '';

    double distance;
    if (distanceValue is int) {
      distance = distanceValue.toDouble();
    } else if (distanceValue is double) {
      distance = distanceValue;
    } else if (distanceValue is String) {
      distance = double.tryParse(distanceValue) ?? double.infinity;
    } else {
      return '';
    }

    if (distance == double.infinity) return '';

    if (distance < 1.0) {
      return '${(distance * 1000).round()}m';
    } else {
      return '${distance.toStringAsFixed(1)}km';
    }
  }

  // 동적 지역 범위 계산 헬퍼 함수
  Map<String, double> _getDynamicBounds({bool forceFullCountry = false}) {
    // 🚀 강제로 전국 범위를 요청하거나 초기 로드인 경우
    if (forceFullCountry || !_isInitialCacheLoaded) {
      DebugLog.log('🇰🇷 전국 범위 사용 (초기 로드 또는 강제 모드)');
      return {
        'swLat': 33.0,  // 제주도 남쪽
        'swLng': 125.0, // 한국 서쪽 경계
        'neLat': 38.7,  // 한국 북쪽 경계
        'neLng': 132.0, // 울릉도 포함 동쪽
      };
    }

    if (currentPosition != null) {
      final lat = currentPosition!.latitude;
      final lng = currentPosition!.longitude;

      // 🚀 개선: 위치 정확도에 따른 동적 반경 조정
      double radius;

      // 위치 정확도가 높을 때 (GPS 정확도 < 50m)
      if (currentPosition!.accuracy < 50) {
        radius = 0.05; // 약 5km - 매우 정확한 위치일 때 가장 가까운 뷰
      }
      // 위치 정확도가 보통일 때 (GPS 정확도 < 100m)
      else if (currentPosition!.accuracy < 100) {
        radius = 0.09; // 약 10km - 일반적인 경우
      }
      // 위치 정확도가 낮을 때 (GPS 정확도 >= 100m)
      else {
        radius = 0.15; // 약 17km - 정확도가 낮을 때 조금 더 넓은 범위
      }

      DebugLog.log('📍 위치 정확도: ${currentPosition!.accuracy.toStringAsFixed(1)}m, 지도 반경: ${(radius * 111).toStringAsFixed(1)}km');

      return {
        'swLat': lat - radius,
        'swLng': lng - radius,
        'neLat': lat + radius,
        'neLng': lng + radius,
      };
    } else {
      // 전국 범위 (한국 전체) - 위치 정보 없을 때 사용
      DebugLog.log('🌍 위치 정보 없음 - 전국 범위 사용');
      return {
        'swLat': 33.0,  // 제주도 남쪽
        'swLng': 125.0, // 한국 서쪽 경계
        'neLat': 38.7,  // 한국 북쪽 경계
        'neLng': 132.0, // 울릉도 포함 동쪽
      };
    }
  }
}