import 'package:json_annotation/json_annotation.dart';
import 'package:hive/hive.dart';

part 'user.g.dart';

@HiveType(typeId: 1)
@JsonSerializable()
class User {
  @HiveField(0)
  final int? id;
  
  @HiveField(1)
  final String email;
  
  @HiveField(2)
  final String? name;
  
  @HiveField(3)
  final String? phone;
  
  @HiveField(4)
  final String? profileImage;
  
  @HiveField(5)
  final List<int>? favoriteAcademies;
  
  @HiveField(6)
  final List<String>? searchHistory;
  
  @HiveField(7)
  final UserPreferences? preferences;
  
  @HiveField(8)
  final DateTime? createdAt;
  
  @HiveField(9)
  final DateTime? updatedAt;
  
  @HiveField(10)
  final bool isEmailVerified;
  
  @HiveField(11)
  final UserType userType;
  
  @HiveField(12)
  final bool isActive;
  
  User({
    this.id,
    required this.email,
    this.name,
    this.phone,
    this.profileImage,
    this.favoriteAcademies,
    this.searchHistory,
    this.preferences,
    this.createdAt,
    this.updatedAt,
    this.isEmailVerified = false,
    this.userType = UserType.regular,
    this.isActive = true,
  });
  
  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  
  Map<String, dynamic> toJson() => _$UserToJson(this);
  
  String get displayName => name ?? email.split('@')[0];
  
  bool get hasFavorites => favoriteAcademies?.isNotEmpty ?? false;
  
  bool get hasSearchHistory => searchHistory?.isNotEmpty ?? false;
  
  User copyWith({
    int? id,
    String? email,
    String? name,
    String? phone,
    String? profileImage,
    List<int>? favoriteAcademies,
    List<String>? searchHistory,
    UserPreferences? preferences,
    DateTime? createdAt,
    DateTime? updatedAt,
    bool? isEmailVerified,
    UserType? userType,
    bool? isActive,
  }) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      name: name ?? this.name,
      phone: phone ?? this.phone,
      profileImage: profileImage ?? this.profileImage,
      favoriteAcademies: favoriteAcademies ?? this.favoriteAcademies,
      searchHistory: searchHistory ?? this.searchHistory,
      preferences: preferences ?? this.preferences,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      isEmailVerified: isEmailVerified ?? this.isEmailVerified,
      userType: userType ?? this.userType,
      isActive: isActive ?? this.isActive,
    );
  }
}

@HiveType(typeId: 2)
@JsonSerializable()
class UserPreferences {
  @HiveField(0)
  final bool enableNotifications;
  
  @HiveField(1)
  final bool enableLocationTracking;
  
  @HiveField(2)
  final String preferredLanguage;
  
  @HiveField(3)
  final ThemeMode themeMode;
  
  @HiveField(4)
  final int maxSearchRadius;
  
  @HiveField(5)
  final List<String> preferredSubjects;
  
  @HiveField(6)
  final List<String> preferredTargets;
  
  @HiveField(7)
  final int maxFee;
  
  @HiveField(8)
  final bool requireParking;
  
  @HiveField(9)
  final bool requireShuttle;
  
  @HiveField(10)
  final bool enableAnalytics;
  
  UserPreferences({
    this.enableNotifications = true,
    this.enableLocationTracking = true,
    this.preferredLanguage = 'ko',
    this.themeMode = ThemeMode.system,
    this.maxSearchRadius = 10,
    this.preferredSubjects = const [],
    this.preferredTargets = const [],
    this.maxFee = 1000000,
    this.requireParking = false,
    this.requireShuttle = false,
    this.enableAnalytics = true,
  });
  
  factory UserPreferences.fromJson(Map<String, dynamic> json) => 
      _$UserPreferencesFromJson(json);
  
  Map<String, dynamic> toJson() => _$UserPreferencesToJson(this);
  
  UserPreferences copyWith({
    bool? enableNotifications,
    bool? enableLocationTracking,
    String? preferredLanguage,
    ThemeMode? themeMode,
    int? maxSearchRadius,
    List<String>? preferredSubjects,
    List<String>? preferredTargets,
    int? maxFee,
    bool? requireParking,
    bool? requireShuttle,
    bool? enableAnalytics,
  }) {
    return UserPreferences(
      enableNotifications: enableNotifications ?? this.enableNotifications,
      enableLocationTracking: enableLocationTracking ?? this.enableLocationTracking,
      preferredLanguage: preferredLanguage ?? this.preferredLanguage,
      themeMode: themeMode ?? this.themeMode,
      maxSearchRadius: maxSearchRadius ?? this.maxSearchRadius,
      preferredSubjects: preferredSubjects ?? this.preferredSubjects,
      preferredTargets: preferredTargets ?? this.preferredTargets,
      maxFee: maxFee ?? this.maxFee,
      requireParking: requireParking ?? this.requireParking,
      requireShuttle: requireShuttle ?? this.requireShuttle,
      enableAnalytics: enableAnalytics ?? this.enableAnalytics,
    );
  }
}

@HiveType(typeId: 3)
enum UserType {
  @HiveField(0)
  regular,
  
  @HiveField(1)
  premium,
  
  @HiveField(2)
  operator,
  
  @HiveField(3)
  admin,
}

@HiveType(typeId: 4)
enum ThemeMode {
  @HiveField(0)
  system,
  
  @HiveField(1)
  light,
  
  @HiveField(2)
  dark,
}