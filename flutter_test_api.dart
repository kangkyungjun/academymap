import 'dart:convert';
import 'package:http/http.dart' as http;

class AcademyApiService {
  static const String baseUrl = 'http://127.0.0.1:8000/api';
  
  // 1. 기본 학원 목록 조회
  static Future<Map<String, dynamic>> getAcademies({
    int page = 1,
    int pageSize = 20,
  }) async {
    final url = '$baseUrl/academies/?page=$page&page_size=$pageSize';
    
    try {
      final response = await http.get(Uri.parse(url));
      
      if (response.statusCode == 200) {
        return json.decode(utf8.decode(response.bodyBytes));
      } else {
        throw Exception('Failed to load academies: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  // 2. 과목별 필터링 테스트
  static Future<List<dynamic>> getFilteredAcademies({
    required double swLat,
    required double swLng, 
    required double neLat,
    required double neLng,
    List<String> subjects = const ['전체'],
    String? priceMin,
    String? priceMax,
    List<String> ageGroups = const [],
    bool shuttleFilter = false,
  }) async {
    const url = 'http://127.0.0.1:8000/api/filtered_academies';
    
    final body = {
      'swLat': swLat,
      'swLng': swLng,
      'neLat': neLat,
      'neLng': neLng,
      'subjects': subjects,
      if (priceMin != null) 'priceMin': priceMin,
      if (priceMax != null) 'priceMax': priceMax,
      'ageGroups': ageGroups,
      'shuttleFilter': shuttleFilter,
    };
    
    try {
      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );
      
      if (response.statusCode == 200) {
        return json.decode(utf8.decode(response.bodyBytes));
      } else {
        throw Exception('Failed to load filtered academies: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  // 3. 근처 학원 조회
  static Future<List<dynamic>> getNearbyAcademies({
    required double lat,
    required double lng,
    double radius = 2.0, // km
    int limit = 20,
  }) async {
    final url = '$baseUrl/academies/nearby/?lat=$lat&lng=$lng&radius=$radius&limit=$limit';
    
    try {
      final response = await http.get(Uri.parse(url));
      
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        return data['results'] ?? [];
      } else {
        throw Exception('Failed to load nearby academies: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  // 4. 학원 상세 정보
  static Future<Map<String, dynamic>> getAcademyDetail(int id) async {
    final url = '$baseUrl/academies/$id/';
    
    try {
      final response = await http.get(Uri.parse(url));
      
      if (response.statusCode == 200) {
        return json.decode(utf8.decode(response.bodyBytes));
      } else {
        throw Exception('Failed to load academy detail: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  // 5. 인기 학원 조회  
  static Future<List<dynamic>> getPopularAcademies({int limit = 10}) async {
    final url = '$baseUrl/academies/popular/?limit=$limit';
    
    try {
      final response = await http.get(Uri.parse(url));
      
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        return data['results'] ?? [];
      } else {
        throw Exception('Failed to load popular academies: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  // 6. 검색
  static Future<List<dynamic>> searchAcademies({
    required String query,
    int page = 1,
    int pageSize = 20,
  }) async {
    final url = '$baseUrl/academies/search/?q=$query&page=$page&page_size=$pageSize';
    
    try {
      final response = await http.get(Uri.parse(url));
      
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        return data['results'] ?? [];
      } else {
        throw Exception('Failed to search academies: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
}

// 테스트 함수들
void main() async {
  print('🚀 Academy API 테스트 시작');
  
  try {
    // 1. 기본 학원 목록 테스트
    print('\n1️⃣ 기본 학원 목록 테스트');
    final academies = await AcademyApiService.getAcademies(page: 1, pageSize: 5);
    print('총 학원 수: ${academies['count']}');
    print('첫 번째 학원: ${academies['results'][0]['상호명']}');
    
    // 2. 과목 필터링 테스트 (수학)
    print('\n2️⃣ 수학 과목 필터링 테스트');
    final mathAcademies = await AcademyApiService.getFilteredAcademies(
      swLat: 37.5,
      swLng: 126.9,
      neLat: 37.6,
      neLng: 127.1,
      subjects: ['수학'],
    );
    print('수학 학원 수: ${mathAcademies.length}');
    if (mathAcademies.isNotEmpty) {
      print('첫 번째 수학 학원: ${mathAcademies[0]['상호명']}');
    }
    
    // 3. 전체 과목 필터링 테스트
    print('\n3️⃣ 전체 과목 필터링 테스트');
    final allAcademies = await AcademyApiService.getFilteredAcademies(
      swLat: 37.5,
      swLng: 126.9,
      neLat: 37.6,
      neLng: 127.1,
      subjects: ['전체'],
    );
    print('전체 학원 수: ${allAcademies.length}');
    
    // 4. 근처 학원 테스트 (강남역 기준)
    print('\n4️⃣ 근처 학원 테스트 (강남역)');
    final nearbyAcademies = await AcademyApiService.getNearbyAcademies(
      lat: 37.498095,
      lng: 127.02761,
      radius: 1.0,
      limit: 5,
    );
    print('강남역 근처 학원 수: ${nearbyAcademies.length}');
    
    // 5. 학원 상세 정보 테스트
    if (academies['results'].isNotEmpty) {
      print('\n5️⃣ 학원 상세 정보 테스트');
      final firstAcademy = academies['results'][0];
      final detail = await AcademyApiService.getAcademyDetail(firstAcademy['id']);
      print('상세 정보: ${detail['상호명']} - ${detail['도로명주소']}');
    }
    
    // 6. 검색 테스트
    print('\n6️⃣ 검색 테스트 (수학)');
    final searchResults = await AcademyApiService.searchAcademies(
      query: '수학',
      pageSize: 3,
    );
    print('수학 검색 결과: ${searchResults.length}개');
    
    // 7. 인기 학원 테스트
    print('\n7️⃣ 인기 학원 테스트');
    final popularAcademies = await AcademyApiService.getPopularAcademies(limit: 3);
    print('인기 학원 수: ${popularAcademies.length}');
    
    print('\n✅ 모든 API 테스트 성공!');
    
  } catch (e) {
    print('❌ API 테스트 실패: $e');
  }
}