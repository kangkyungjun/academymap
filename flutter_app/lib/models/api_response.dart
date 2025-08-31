import 'package:json_annotation/json_annotation.dart';

part 'api_response.g.dart';

@JsonSerializable(genericArgumentFactories: true)
class ApiResponse<T> {
  final bool success;
  final String message;
  final T? data;
  final Map<String, dynamic>? meta;
  final List<ApiError>? errors;
  final int? statusCode;
  
  ApiResponse({
    required this.success,
    required this.message,
    this.data,
    this.meta,
    this.errors,
    this.statusCode,
  });
  
  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Object? json) fromJsonT,
  ) => _$ApiResponseFromJson(json, fromJsonT);
  
  Map<String, dynamic> toJson(Object Function(T value) toJsonT) =>
      _$ApiResponseToJson(this, toJsonT);
  
  factory ApiResponse.success({
    required T data,
    String message = 'Success',
    Map<String, dynamic>? meta,
  }) {
    return ApiResponse<T>(
      success: true,
      message: message,
      data: data,
      meta: meta,
    );
  }
  
  factory ApiResponse.error({
    required String message,
    List<ApiError>? errors,
    int? statusCode,
    Map<String, dynamic>? meta,
  }) {
    return ApiResponse<T>(
      success: false,
      message: message,
      errors: errors,
      statusCode: statusCode,
      meta: meta,
    );
  }
  
  bool get isSuccess => success;
  bool get isError => !success;
  bool get hasData => data != null;
  bool get hasErrors => errors?.isNotEmpty ?? false;
  bool get hasMeta => meta?.isNotEmpty ?? false;
}

@JsonSerializable()
class ApiError {
  final String field;
  final String message;
  final String? code;
  
  ApiError({
    required this.field,
    required this.message,
    this.code,
  });
  
  factory ApiError.fromJson(Map<String, dynamic> json) => _$ApiErrorFromJson(json);
  
  Map<String, dynamic> toJson() => _$ApiErrorToJson(this);
}

@JsonSerializable(genericArgumentFactories: true)
class PaginatedResponse<T> {
  final List<T> results;
  final int count;
  final int? totalPages;
  final int? currentPage;
  final String? next;
  final String? previous;
  final Map<String, dynamic>? filters;
  
  PaginatedResponse({
    required this.results,
    required this.count,
    this.totalPages,
    this.currentPage,
    this.next,
    this.previous,
    this.filters,
  });
  
  factory PaginatedResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Object? json) fromJsonT,
  ) => _$PaginatedResponseFromJson(json, fromJsonT);
  
  Map<String, dynamic> toJson(Object Function(T value) toJsonT) =>
      _$PaginatedResponseToJson(this, toJsonT);
  
  bool get hasNext => next != null;
  bool get hasPrevious => previous != null;
  bool get isEmpty => results.isEmpty;
  bool get isNotEmpty => results.isNotEmpty;
  int get length => results.length;
  
  PaginatedResponse<T> copyWith({
    List<T>? results,
    int? count,
    int? totalPages,
    int? currentPage,
    String? next,
    String? previous,
    Map<String, dynamic>? filters,
  }) {
    return PaginatedResponse<T>(
      results: results ?? this.results,
      count: count ?? this.count,
      totalPages: totalPages ?? this.totalPages,
      currentPage: currentPage ?? this.currentPage,
      next: next ?? this.next,
      previous: previous ?? this.previous,
      filters: filters ?? this.filters,
    );
  }
}

@JsonSerializable()
class AuthResponse {
  final User? user;
  final String? accessToken;
  final String? refreshToken;
  final DateTime? expiresAt;
  final String? tokenType;
  
  AuthResponse({
    this.user,
    this.accessToken,
    this.refreshToken,
    this.expiresAt,
    this.tokenType = 'Bearer',
  });
  
  factory AuthResponse.fromJson(Map<String, dynamic> json) => 
      _$AuthResponseFromJson(json);
  
  Map<String, dynamic> toJson() => _$AuthResponseToJson(this);
  
  bool get hasValidToken => 
      accessToken != null && 
      (expiresAt == null || expiresAt!.isAfter(DateTime.now()));
  
  bool get isExpired => 
      expiresAt != null && expiresAt!.isBefore(DateTime.now());
  
  bool get needsRefresh => 
      accessToken != null && 
      expiresAt != null && 
      expiresAt!.difference(DateTime.now()).inMinutes < 30;
}

class User {
  final int id;
  final String email;
  final String? name;
  final String? phone;
  final String? profileImage;
  final bool isEmailVerified;
  
  User({
    required this.id,
    required this.email,
    this.name,
    this.phone,
    this.profileImage,
    this.isEmailVerified = false,
  });
  
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      email: json['email'] as String,
      name: json['name'] as String?,
      phone: json['phone'] as String?,
      profileImage: json['profile_image'] as String?,
      isEmailVerified: json['is_email_verified'] as bool? ?? false,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'name': name,
      'phone': phone,
      'profile_image': profileImage,
      'is_email_verified': isEmailVerified,
    };
  }
}