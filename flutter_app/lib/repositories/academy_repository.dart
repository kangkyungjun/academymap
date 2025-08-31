import '../models/academy.dart';
import '../models/api_response.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';

class AcademyRepository {
  final ApiService _apiService;
  
  AcademyRepository(this._apiService);
  
  Future<PaginatedResponse<Academy>> getAcademies({
    int page = 1,
    int pageSize = AppConstants.defaultPageSize,
    String? search,
    String? subject,
    String? target,
    double? latitude,
    double? longitude,
    double? radius,
    int? minFee,
    int? maxFee,
    double? minRating,
    bool? hasShuttle,
    bool? hasParking,
    bool? hasOnline,
    String? ordering,
  }) async {
    try {
      final response = await _apiService.getAcademies(
        page: page,
        pageSize: pageSize,
        search: search,
        subject: subject,
        target: target,
        latitude: latitude,
        longitude: longitude,
        radius: radius,
        minFee: minFee,
        maxFee: maxFee,
        minRating: minRating,
        hasShuttle: hasShuttle,
        hasParking: hasParking,
        hasOnline: hasOnline,
        ordering: ordering,
      );
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('학원 목록을 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<Academy> getAcademy(int id) async {
    try {
      final response = await _apiService.getAcademy(id);
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('학원 정보를 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<List<Academy>> getNearbyAcademies({
    required double latitude,
    required double longitude,
    double radius = 5.0,
    int limit = 20,
  }) async {
    try {
      final response = await _apiService.getNearbyAcademies(
        latitude: latitude,
        longitude: longitude,
        radius: radius,
        limit: limit,
      );
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('근처 학원을 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<PaginatedResponse<Academy>> searchAcademies({
    required String query,
    int page = 1,
    int pageSize = AppConstants.defaultPageSize,
    double? latitude,
    double? longitude,
  }) async {
    try {
      final response = await _apiService.searchAcademies(
        query: query,
        page: page,
        pageSize: pageSize,
        latitude: latitude,
        longitude: longitude,
      );
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('학원 검색에 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<List<Region>> getRegions() async {
    try {
      final response = await _apiService.getRegions();
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('지역 정보를 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<PaginatedResponse<Academy>> getAcademiesByRegion(
    String regionCode, {
    int page = 1,
    int pageSize = AppConstants.defaultPageSize,
  }) async {
    try {
      final response = await _apiService.getAcademiesByRegion(
        regionCode,
        page: page,
        pageSize: pageSize,
      );
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('지역별 학원을 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<PaginatedResponse<Academy>> getFavoriteAcademies({
    int page = 1,
    int pageSize = AppConstants.defaultPageSize,
  }) async {
    try {
      final response = await _apiService.getFavoriteAcademies(
        page: page,
        pageSize: pageSize,
      );
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('즐겨찾기 학원을 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<bool> addToFavorites(int academyId) async {
    try {
      final response = await _apiService.addToFavorites(academyId);
      
      if (response.isSuccess) {
        return true;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('즐겨찾기 추가에 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<bool> removeFromFavorites(int academyId) async {
    try {
      final response = await _apiService.removeFromFavorites(academyId);
      
      if (response.isSuccess) {
        return true;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('즐겨찾기 제거에 실패했습니다: ${e.toString()}');
    }
  }
}

class UserRepository {
  final ApiService _apiService;
  
  UserRepository(this._apiService);
  
  Future<User> getProfile() async {
    try {
      final response = await _apiService.getProfile();
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('프로필을 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<User> updateProfile({
    String? name,
    String? phone,
    String? profileImage,
  }) async {
    try {
      final request = UpdateProfileRequest(
        name: name,
        phone: phone,
        profileImage: profileImage,
      );
      
      final response = await _apiService.updateProfile(request);
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('프로필 업데이트에 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<List<String>> getSearchHistory() async {
    try {
      final response = await _apiService.getSearchHistory();
      
      if (response.isSuccess && response.data != null) {
        return response.data!;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('검색 기록을 불러오는데 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<bool> addSearchHistory(String query) async {
    try {
      final request = AddSearchHistoryRequest(query: query);
      final response = await _apiService.addSearchHistory(request);
      
      if (response.isSuccess) {
        return true;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('검색 기록 추가에 실패했습니다: ${e.toString()}');
    }
  }
  
  Future<bool> clearSearchHistory() async {
    try {
      final response = await _apiService.clearSearchHistory();
      
      if (response.isSuccess) {
        return true;
      } else {
        throw Exception(response.message);
      }
    } catch (e) {
      throw Exception('검색 기록 삭제에 실패했습니다: ${e.toString()}');
    }
  }
}