import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:html' as html;
import 'dart:js' as js;
import 'dart:async';
import 'package:webview_flutter/webview_flutter.dart';
import 'dart:ui_web' as ui_web;
import 'package:geolocator/geolocator.dart';

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

  List<dynamic> academies = [];
  bool isLoading = false;
  String selectedSubject = '전체';
  int totalCount = 0;

  // 고급 필터링 변수들
  RangeValues priceRange = const RangeValues(0, 2000000);
  List<String> selectedAgeGroups = [];
  bool shuttleFilter = false;
  bool showAdvancedFilters = false;
  
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

  // 오류 상태
  String? errorMessage;
  bool hasNetworkError = false;

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
            Future.delayed(Duration(milliseconds: 2000), () {
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
    super.dispose();
  }
  
  void _onScroll() {
    if (scrollController.position.pixels >= scrollController.position.maxScrollExtent - 200) {
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
        print('🔍 위치 서비스가 비활성화되어 있습니다');
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
          print('🚫 위치 권한이 거부되었습니다');
          setState(() {
            isLocationLoading = false;
          });
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        print('🚫 위치 권한이 영구적으로 거부되었습니다');
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

      print('📍 현재 위치 획득: ${position.latitude}, ${position.longitude}');

      // 지도가 이미 표시 중이면 위치 업데이트
      if (isMapView) {
        _sendLocationToMap();
      }

    } catch (e) {
      print('❌ 위치 획득 실패: $e');
      setState(() {
        isLocationLoading = false;
      });
    }
  }

  void _sendLocationToMap() {
    try {
      final iframe = html.document.querySelector('iframe') as html.IFrameElement?;
      print('🔍 iframe 확인: ${iframe != null}, contentWindow: ${iframe?.contentWindow != null}, currentPosition: ${currentPosition != null}');
      
      if (iframe?.contentWindow != null && currentPosition != null) {
        final message = {
          'type': 'setMapCenter',
          'lat': currentPosition!.latitude,
          'lng': currentPosition!.longitude,
        };
        print('📤 전송할 메시지: $message');
        
        iframe!.contentWindow!.postMessage(message, '*');
        print('📍 현재 위치를 지도에 전송 완료: ${currentPosition!.latitude}, ${currentPosition!.longitude}');
      } else {
        print('❌ iframe 또는 위치 정보가 없습니다. iframe: ${iframe != null}, position: ${currentPosition != null}');
      }
    } catch (e) {
      print('위치 전송 오류: $e');
    }
  }

  void _setupMessageListener() {
    // iframe에서 오는 메시지 수신
    html.window.addEventListener('message', (event) {
      final messageEvent = event as html.MessageEvent;
      if (messageEvent.data != null && messageEvent.data is Map) {
        final data = messageEvent.data as Map;
        if (data['type'] == 'requestLocation') {
          print('📍 지도에서 현재 위치 요청');
          _getCurrentLocation().then((_) {
            if (currentPosition != null) {
              _sendLocationToMap();
            }
          });
        } else if (data['type'] == 'requestMarkersInBounds') {
          print('🗺️ 지도 영역 내 마커 요청');
          final boundsData = data['data'] as Map;
          _loadMarkersInBounds(
            boundsData['sw_lat'],
            boundsData['sw_lng'], 
            boundsData['ne_lat'],
            boundsData['ne_lng'],
          );
        } else if (data['type'] == 'currentBoundsResponse') {
          print('🗺️ 현재 지도 영역 응답 받음');
          final boundsData = data['data'] as Map;
          _loadMarkersInBounds(
            boundsData['sw_lat'],
            boundsData['sw_lng'], 
            boundsData['ne_lat'],
            boundsData['ne_lng'],
          );
        } else if (data['type'] == 'requestClustersInBounds') {
          print('🏘️ 지도 영역 내 클러스터 요청');
          final boundsData = data['data'] as Map;
          _loadClustersInBounds(
            boundsData['sw_lat'],
            boundsData['sw_lng'],
            boundsData['ne_lat'],
            boundsData['ne_lng'],
          );
        } else if (data['type'] == 'mapInitialized') {
          print('ℹ️ 지도 초기화 완료 이벤트 수신');
          if (currentPosition != null) {
            print('📍 지도 초기화 완료 - 사용자 위치로 중심 이동');
            _sendLocationToMap();
          }
        }
      }
    });
  }

  Future<void> _loadMarkersInBounds(double swLat, double swLng, double neLat, double neLng) async {
    try {
      final Uri uri = Uri.parse('$apiBaseUrl/api/v1/academies/').replace(queryParameters: {
        'sw_lat': swLat.toString(),
        'sw_lng': swLng.toString(),
        'ne_lat': neLat.toString(),
        'ne_lng': neLng.toString(),
        'limit': '200', // 지도 영역 내에서는 더 많은 마커 표시
        ...getFilterParams(),
      });

      print('🌐 지도 영역 API 요청: $uri');
      final response = await http.get(uri);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final allAcademies = data['results'] ?? [];
        
        // 클라이언트 사이드에서 bounds 필터링 (임시로 범위 확대)
        final boundsAcademies = allAcademies.where((academy) {
          final lat = academy['위도'];
          final lng = academy['경도'];
          
          if (lat == null || lng == null) return false;
          
          // 임시로 bounds 범위를 크게 확장 (±0.5도 = 약 55km)
          final expandedSwLat = swLat - 0.5;
          final expandedNeLat = neLat + 0.5;
          final expandedSwLng = swLng - 0.5;
          final expandedNeLng = neLng + 0.5;
          
          return lat >= expandedSwLat && lat <= expandedNeLat && lng >= expandedSwLng && lng <= expandedNeLng;
        }).toList();
        
        print('📍 지도 영역 내 학원: ${boundsAcademies.length}개 (전체: ${allAcademies.length}개)');
        print('✅ 지도 영역 마커 업데이트: ${boundsAcademies.length}개');
        
        // iframe에 마커 업데이트 메시지 전송
        _sendMarkersToMap(boundsAcademies.take(200).toList()); // 최대 200개로 제한
      } else {
        print('❌ API 응답 오류: ${response.statusCode}');
        print('📄 응답 내용: ${response.body}');
        
        // 에러 상황에서도 빈 배열로 마커 클리어
        if (response.statusCode == 429) {
          print('🚨 API Throttling 발생 - 잠시 후 다시 시도됩니다');
        }
        _sendMarkersToMap([]);
      }
    } catch (e) {
      print('지도 영역 마커 로드 오류: $e');
    }
  }

  Map<String, String> getFilterParams() {
    Map<String, String> params = {};
    
    // 과목 카테고리 필터
    if (selectedSubject != '전체') {
      params['category'] = selectedSubject;
    }
    
    // 가격 범위 필터
    if (priceRange.start > 0 || priceRange.end < 2000000) {
      params['priceMin'] = priceRange.start.toString();
      params['priceMax'] = priceRange.end >= 2000000 ? '999999999' : priceRange.end.toString();
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
    try {
      final Uri uri = Uri.parse('$apiBaseUrl/map_api/clusters/').replace(queryParameters: {
        'sw_lat': swLat.toString(),
        'sw_lng': swLng.toString(),
        'ne_lat': neLat.toString(),
        'ne_lng': neLng.toString(),
        ...getFilterParams(),
      });

      print('🏘️ 클러스터 API 요청: $uri');
      final response = await http.get(uri);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final clusters = data['clusters'] ?? [];
        
        print('🏘️ 지도 영역 내 클러스터: ${clusters.length}개');
        print('✅ 지도 영역 클러스터 업데이트: ${clusters.length}개');
        
        // iframe에 클러스터 업데이트 메시지 전송
        _sendClustersToMap(clusters);
      } else {
        print('❌ 클러스터 API 응답 오류: ${response.statusCode}');
        print('📄 응답 내용: ${response.body}');
        
        // 에러 상황에서도 빈 배열로 클러스터 클리어
        if (response.statusCode == 429) {
          print('🚨 클러스터 API Throttling 발생 - 잠시 후 다시 시도됩니다');
        }
        _sendClustersToMap([]);
      }
    } catch (e) {
      print('클러스터 로드 오류: $e');
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
        print('✅ 지도 영역 클러스터 업데이트: ${clustersData.length}개');
      } else {
        print('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      print('클러스터 전송 오류: $e');
    }
  }

  void _sendMarkersToMap(List<dynamic> academiesData) {
    try {
      // 학원 데이터를 지도 마커로 변환
      final markersData = academiesData.map((academy) {
        return {
          'name': academy['상호명'] ?? '학원',
          'lat': academy['위도'],
          'lng': academy['경도'], 
          'address': academy['도로명주소'] ?? '',
          'subject': _getAcademySubjects(academy),
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
        print('✅ 지도 영역 마커 업데이트: ${markersData.length}개');
      } else {
        print('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      print('지도 마커 전송 오류: $e');
    }
  }

  bool _hasActiveFilters() {
    return selectedSubject != '전체' ||
           priceRange.start > 0 ||
           priceRange.end < 2000000 ||
           selectedAgeGroups.isNotEmpty ||
           shuttleFilter;
  }

  List<Widget> _getActiveFilterChips() {
    List<Widget> chips = [];

    // 과목 필터
    if (selectedSubject != '전체') {
      chips.add(
        Chip(
          label: Text('📚 $selectedSubject'),
          backgroundColor: Colors.blue[100],
          labelStyle: TextStyle(fontSize: 11, color: Colors.blue[800]),
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      );
    }

    // 가격 필터
    if (priceRange.start > 0 || priceRange.end < 2000000) {
      String priceText = '💰 ';
      if (priceRange.start > 0 && priceRange.end < 2000000) {
        priceText += '${(priceRange.start / 10000).toInt()}만~${priceRange.end >= 2000000 ? '200만+' : '${(priceRange.end / 10000).toInt()}만'}원';
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
      print('🔍 현재 지도 영역에서 필터 적용 요청');
    }
  }

  Future<void> loadAcademies() async {
    if (!mounted) return;
    
    setState(() {
      isLoading = true;
      errorMessage = null;
      hasNetworkError = false;
    });

    print('🔍 필터링 시작: $selectedSubject'); // 디버깅용

    try {
      final response = await http.post(
        Uri.parse('$apiBaseUrl/api/filtered_academies'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'swLat': _getDynamicBounds()['swLat'],
          'swLng': _getDynamicBounds()['swLng'],
          'neLat': _getDynamicBounds()['neLat'],
          'neLng': _getDynamicBounds()['neLng'],
          'subjects': [selectedSubject],
          'priceMin': priceRange.start.toString(),
          'priceMax': priceRange.end >= 2000000 ? '999999999' : priceRange.end.toString(),
          'ageGroups': selectedAgeGroups,
          'shuttleFilter': shuttleFilter,
          'searchQuery': searchQuery.trim(),
        }),
      );

      print('📡 API 응답 코드: ${response.statusCode}'); // 디버깅용

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(utf8.decode(response.bodyBytes));
        print('📊 받은 데이터 수: ${data.length}개'); // 디버깅용
        
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
        
        print('✅ UI 업데이트 완료: ${academies.length}개 표시'); // 디버깅용
        
        // 지도가 활성화되어 있으면 마커 업데이트
        if (isMapView) {
          Future.delayed(Duration(milliseconds: 300), () {
            _addAcademyMarkersToMap();
          });
        }
      } else {
        throw Exception('서버 오류: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ 오류 발생: $e'); // 디버깅용
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
      
      print('📄 페이지 $currentPage 로드: ${newAcademies.length}개 추가 (총 ${academies.length}개)');
      
    } catch (e) {
      print('❌ 추가 로딩 오류: $e');
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
        'name': academy['상호명'] ?? '학원',
        'lat': academy['위도'],
        'lng': academy['경도'], 
        'address': academy['도로명주소'] ?? '',
        'subject': _getAcademySubjects(academy),
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
        print('✅ iframe에 ${markersData.length}개 마커 데이터 전송');
      } else {
        print('❌ iframe을 찾을 수 없습니다');
      }
    } catch (e) {
      print('마커 업데이트 오류: $e');
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
                    _sendLocationToMap();
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
      body: Column(
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
                          selectedSubject = '전체';
                          priceRange = const RangeValues(0, 2000000);
                          selectedAgeGroups.clear();
                          shuttleFilter = false;
                        });
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('🔄 필터가 초기화되었습니다'),
                            duration: Duration(seconds: 2),
                          ),
                        );
                        Future.delayed(Duration(milliseconds: 300), () {
                          applyFiltersWithinMapBounds();
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
                    return FilterChip(
                      label: Text(subject),
                      selected: selectedSubject == subject,
                      onSelected: (bool selected) {
                        if (selected && selectedSubject != subject) {
                          print('🎯 과목 선택: $selectedSubject → $subject'); // 디버깅용
                          setState(() {
                            selectedSubject = subject;
                          });
                          // 약간의 지연을 두어 UI 업데이트 후 현재 지도 영역에서 필터 적용
                          Future.delayed(Duration(milliseconds: 100), () {
                            applyFiltersWithinMapBounds();
                          });
                        }
                      },
                      selectedColor: Colors.blue[100],
                      checkmarkColor: Colors.blue[800],
                    );
                  }).toList(),
                ),
                if (totalCount > 0) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.blue[50],
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '📊 "$selectedSubject" 학원 $totalCount개 중 ${academies.length}개 표시${hasMoreData ? ' (스크롤하여 더 보기)' : ''}',
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
                        '${priceRange.start.toInt().toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (Match m) => '${m[1]},')}원 - ${priceRange.end >= 2000000 ? '200만원 이상' : '${priceRange.end.toInt().toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (Match m) => '${m[1]},')}원'}',
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 14,
                        ),
                      ),
                      RangeSlider(
                        values: priceRange,
                        min: 0,
                        max: 2000000,
                        divisions: 20,
                        labels: RangeLabels(
                          '${(priceRange.start / 10000).toInt()}만원',
                          priceRange.end >= 2000000 ? '200만원+' : '${(priceRange.end / 10000).toInt()}만원',
                        ),
                        onChanged: (RangeValues values) {
                          setState(() {
                            priceRange = values;
                          });
                        },
                        onChangeEnd: (RangeValues values) {
                          Future.delayed(Duration(milliseconds: 300), () {
                            applyFiltersWithinMapBounds();
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
                                applyFiltersWithinMapBounds();
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
                            applyFiltersWithinMapBounds();
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
                                leading: CircleAvatar(
                                  backgroundColor: Colors.blue[100],
                                  child: const Icon(
                                    Icons.school,
                                    color: Colors.blue,
                                  ),
                                ),
                                title: Text(
                                  academy['상호명'] ?? '이름 없음',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
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
                                        Icon(
                                          Icons.location_on,
                                          size: 16,
                                          color: Colors.red[400],
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          '${_safeSubstring(academy['위도']?.toString(), 7)}, ${_safeSubstring(academy['경도']?.toString(), 8)}',
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: Colors.grey[500],
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
                                  _showAcademyDetail(academy);
                                },
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: isLoading ? null : () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('🔄 데이터 새로고침 중...'),
              duration: Duration(seconds: 1),
            ),
          );
          loadAcademies();
        },
        tooltip: '새로고침',
        icon: isLoading 
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.refresh),
        label: Text(isLoading ? '로딩 중' : '새로고침'),
        backgroundColor: isLoading ? Colors.grey : null,
      ),
    );
  }

  // 안전한 substring 처리를 위한 헬퍼 함수
  String _safeSubstring(String? str, int maxLength) {
    if (str == null || str.isEmpty) return 'N/A';
    return str.length <= maxLength ? str : str.substring(0, maxLength);
  }

  // 동적 지역 범위 계산 헬퍼 함수
  Map<String, double> _getDynamicBounds() {
    if (currentPosition != null) {
      // 사용자 위치 기준 반경 약 50km 범위
      final lat = currentPosition!.latitude;
      final lng = currentPosition!.longitude;
      const radius = 0.45; // 약 50km에 해당하는 위도/경도 차이

      return {
        'swLat': lat - radius,
        'swLng': lng - radius,
        'neLat': lat + radius,
        'neLng': lng + radius,
      };
    } else {
      // 전국 범위 (한국 전체)
      return {
        'swLat': 33.0,  // 제주도 남쪽
        'swLng': 125.0, // 한국 서쪽 경계
        'neLat': 38.7,  // 한국 북쪽 경계
        'neLng': 132.0, // 울릉도 포함 동쪽
      };
    }
  }
}