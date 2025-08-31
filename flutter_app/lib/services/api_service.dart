import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';
import 'package:json_annotation/json_annotation.dart';

import '../models/academy.dart';
import '../models/api_response.dart';
import '../utils/constants.dart';

part 'api_service.g.dart';

@RestApi()
abstract class ApiService {
  factory ApiService(Dio dio, {String baseUrl}) = _ApiService;
  
  factory ApiService.create({String? baseUrl}) {
    final dio = Dio();
    
    dio.options = BaseOptions(
      baseUrl: baseUrl ?? AppConstants.apiBaseUrl,
      connectTimeout: AppConstants.connectionTimeout,
      receiveTimeout: AppConstants.receiveTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );
    
    dio.interceptors.addAll([
      LogInterceptor(
        requestBody: AppConstants.enableLogging,
        responseBody: AppConstants.enableLogging,
        requestHeader: AppConstants.enableLogging,
        responseHeader: false,
        error: true,
      ),
      AuthInterceptor(),
      ErrorInterceptor(),
    ]);
    
    return ApiService(dio, baseUrl: baseUrl ?? AppConstants.apiBaseUrl);
  }
  
  @GET('${AppConstants.apiV1Path}/academies/')
  Future<ApiResponse<PaginatedResponse<Academy>>> getAcademies({
    @Query('page') int page = 1,
    @Query('page_size') int pageSize = AppConstants.defaultPageSize,
    @Query('search') String? search,
    @Query('subject') String? subject,
    @Query('target') String? target,
    @Query('latitude') double? latitude,
    @Query('longitude') double? longitude,
    @Query('radius') double? radius,
    @Query('min_fee') int? minFee,
    @Query('max_fee') int? maxFee,
    @Query('rating') double? minRating,
    @Query('has_shuttle') bool? hasShuttle,
    @Query('has_parking') bool? hasParking,
    @Query('has_online') bool? hasOnline,
    @Query('ordering') String? ordering,
  });
  
  @GET('${AppConstants.apiV1Path}/academies/{id}/')
  Future<ApiResponse<Academy>> getAcademy(@Path('id') int id);
  
  @GET('${AppConstants.apiV1Path}/academies/nearby/')
  Future<ApiResponse<List<Academy>>> getNearbyAcademies({
    @Query('latitude') required double latitude,
    @Query('longitude') required double longitude,
    @Query('radius') double radius = 5.0,
    @Query('limit') int limit = 20,
  });
  
  @GET('${AppConstants.apiV1Path}/academies/search/')
  Future<ApiResponse<PaginatedResponse<Academy>>> searchAcademies({
    @Query('q') required String query,
    @Query('page') int page = 1,
    @Query('page_size') int pageSize = AppConstants.defaultPageSize,
    @Query('latitude') double? latitude,
    @Query('longitude') double? longitude,
  });
  
  @GET('${AppConstants.apiV1Path}/regions/')
  Future<ApiResponse<List<Region>>> getRegions();
  
  @GET('${AppConstants.apiV1Path}/regions/{code}/academies/')
  Future<ApiResponse<PaginatedResponse<Academy>>> getAcademiesByRegion(
    @Path('code') String regionCode, {
    @Query('page') int page = 1,
    @Query('page_size') int pageSize = AppConstants.defaultPageSize,
  });
  
  @POST('${AppConstants.apiV1Path}/auth/login/')
  Future<ApiResponse<AuthResponse>> login(@Body() LoginRequest request);
  
  @POST('${AppConstants.apiV1Path}/auth/register/')
  Future<ApiResponse<AuthResponse>> register(@Body() RegisterRequest request);
  
  @POST('${AppConstants.apiV1Path}/auth/refresh/')
  Future<ApiResponse<AuthResponse>> refreshToken(@Body() RefreshTokenRequest request);
  
  @POST('${AppConstants.apiV1Path}/auth/logout/')
  Future<ApiResponse<void>> logout();
  
  @GET('${AppConstants.apiV1Path}/user/profile/')
  Future<ApiResponse<User>> getProfile();
  
  @PUT('${AppConstants.apiV1Path}/user/profile/')
  Future<ApiResponse<User>> updateProfile(@Body() UpdateProfileRequest request);
  
  @GET('${AppConstants.apiV1Path}/user/favorites/')
  Future<ApiResponse<PaginatedResponse<Academy>>> getFavoriteAcademies({
    @Query('page') int page = 1,
    @Query('page_size') int pageSize = AppConstants.defaultPageSize,
  });
  
  @POST('${AppConstants.apiV1Path}/user/favorites/{academyId}/')
  Future<ApiResponse<void>> addToFavorites(@Path('academyId') int academyId);
  
  @DELETE('${AppConstants.apiV1Path}/user/favorites/{academyId}/')
  Future<ApiResponse<void>> removeFromFavorites(@Path('academyId') int academyId);
  
  @GET('${AppConstants.apiV1Path}/user/search-history/')
  Future<ApiResponse<List<String>>> getSearchHistory();
  
  @POST('${AppConstants.apiV1Path}/user/search-history/')
  Future<ApiResponse<void>> addSearchHistory(@Body() AddSearchHistoryRequest request);
  
  @DELETE('${AppConstants.apiV1Path}/user/search-history/')
  Future<ApiResponse<void>> clearSearchHistory();
}

@JsonSerializable()
class LoginRequest {
  final String email;
  final String password;
  
  LoginRequest({required this.email, required this.password});
  
  factory LoginRequest.fromJson(Map<String, dynamic> json) => 
      _$LoginRequestFromJson(json);
  
  Map<String, dynamic> toJson() => _$LoginRequestToJson(this);
}

@JsonSerializable()
class RegisterRequest {
  final String email;
  final String password;
  final String? name;
  final String? phone;
  
  RegisterRequest({
    required this.email,
    required this.password,
    this.name,
    this.phone,
  });
  
  factory RegisterRequest.fromJson(Map<String, dynamic> json) => 
      _$RegisterRequestFromJson(json);
  
  Map<String, dynamic> toJson() => _$RegisterRequestToJson(this);
}

@JsonSerializable()
class RefreshTokenRequest {
  final String refreshToken;
  
  RefreshTokenRequest({required this.refreshToken});
  
  factory RefreshTokenRequest.fromJson(Map<String, dynamic> json) => 
      _$RefreshTokenRequestFromJson(json);
  
  Map<String, dynamic> toJson() => _$RefreshTokenRequestToJson(this);
}

@JsonSerializable()
class UpdateProfileRequest {
  final String? name;
  final String? phone;
  final String? profileImage;
  
  UpdateProfileRequest({this.name, this.phone, this.profileImage});
  
  factory UpdateProfileRequest.fromJson(Map<String, dynamic> json) => 
      _$UpdateProfileRequestFromJson(json);
  
  Map<String, dynamic> toJson() => _$UpdateProfileRequestToJson(this);
}

@JsonSerializable()
class AddSearchHistoryRequest {
  final String query;
  
  AddSearchHistoryRequest({required this.query});
  
  factory AddSearchHistoryRequest.fromJson(Map<String, dynamic> json) => 
      _$AddSearchHistoryRequestFromJson(json);
  
  Map<String, dynamic> toJson() => _$AddSearchHistoryRequestToJson(this);
}

@JsonSerializable()
class Region {
  final String code;
  final String name;
  final String? parentCode;
  final List<Region>? children;
  
  Region({
    required this.code,
    required this.name,
    this.parentCode,
    this.children,
  });
  
  factory Region.fromJson(Map<String, dynamic> json) => _$RegionFromJson(json);
  
  Map<String, dynamic> toJson() => _$RegionToJson(this);
}

class AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    try {
      final token = await _getStoredToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    } catch (e) {
      print('Error getting stored token: $e');
    }
    
    handler.next(options);
  }
  
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      try {
        final newToken = await _refreshToken();
        if (newToken != null) {
          err.requestOptions.headers['Authorization'] = 'Bearer $newToken';
          final dio = Dio();
          final response = await dio.fetch(err.requestOptions);
          handler.resolve(response);
          return;
        }
      } catch (e) {
        print('Token refresh failed: $e');
        await _clearStoredTokens();
      }
    }
    
    handler.next(err);
  }
  
  Future<String?> _getStoredToken() async {
    return null;
  }
  
  Future<String?> _refreshToken() async {
    return null;
  }
  
  Future<void> _clearStoredTokens() async {
  }
}

class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    String message;
    
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        message = AppConstants.errorNetworkConnection;
        break;
      case DioExceptionType.connectionError:
        message = AppConstants.errorNetworkConnection;
        break;
      case DioExceptionType.badResponse:
        message = _handleResponseError(err.response);
        break;
      default:
        message = AppConstants.errorUnknown;
    }
    
    final error = DioException(
      requestOptions: err.requestOptions,
      type: err.type,
      message: message,
      response: err.response,
    );
    
    handler.next(error);
  }
  
  String _handleResponseError(Response? response) {
    if (response == null) return AppConstants.errorServerError;
    
    switch (response.statusCode) {
      case 400:
        try {
          final data = response.data;
          if (data is Map<String, dynamic> && data.containsKey('message')) {
            return data['message'];
          }
        } catch (e) {
        }
        return '잘못된 요청입니다.';
      case 401:
        return '인증이 필요합니다.';
      case 403:
        return '접근 권한이 없습니다.';
      case 404:
        return '요청한 정보를 찾을 수 없습니다.';
      case 500:
        return AppConstants.errorServerError;
      default:
        return AppConstants.errorUnknown;
    }
  }
}