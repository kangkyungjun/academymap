import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:kakao_flutter_sdk/kakao_flutter_sdk.dart';

import '../models/api_response.dart';
import '../utils/constants.dart';
import 'api_service.dart';

class AuthService extends ChangeNotifier {
  User? _user;
  String? _accessToken;
  String? _refreshToken;
  bool _isLoading = false;
  bool _isAuthenticated = false;
  
  final ApiService _apiService;
  final GoogleSignIn _googleSignIn;
  
  AuthService({ApiService? apiService})
      : _apiService = apiService ?? ApiService.create(),
        _googleSignIn = GoogleSignIn(
          scopes: ['email', 'profile'],
        );
  
  User? get user => _user;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _isAuthenticated && _user != null;
  String? get accessToken => _accessToken;
  
  Future<void> initialize() async {
    await loadUserFromStorage();
  }
  
  Future<void> loadUserFromStorage() async {
    try {
      _setLoading(true);
      
      final prefs = await SharedPreferences.getInstance();
      final accessToken = prefs.getString(AppConstants.keyAccessToken);
      final refreshToken = prefs.getString(AppConstants.keyRefreshToken);
      final userData = prefs.getString(AppConstants.keyUserData);
      
      if (accessToken != null && userData != null) {
        _accessToken = accessToken;
        _refreshToken = refreshToken;
        
        try {
          final userJson = Map<String, dynamic>.from(
            await _parseUserData(userData),
          );
          _user = User.fromJson(userJson);
          _isAuthenticated = true;
          
          await _validateAndRefreshToken();
        } catch (e) {
          print('Error parsing stored user data: $e');
          await _clearStoredAuth();
        }
      }
    } catch (e) {
      print('Error loading user from storage: $e');
      await _clearStoredAuth();
    } finally {
      _setLoading(false);
    }
  }
  
  Future<bool> login(String email, String password) async {
    try {
      _setLoading(true);
      
      final request = LoginRequest(email: email, password: password);
      final response = await _apiService.login(request);
      
      if (response.isSuccess && response.data != null) {
        await _handleAuthSuccess(response.data!);
        return true;
      } else {
        _handleAuthError(response.message);
        return false;
      }
    } catch (e) {
      _handleAuthError('로그인 중 오류가 발생했습니다: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<bool> register(String email, String password, {String? name, String? phone}) async {
    try {
      _setLoading(true);
      
      final request = RegisterRequest(
        email: email,
        password: password,
        name: name,
        phone: phone,
      );
      
      final response = await _apiService.register(request);
      
      if (response.isSuccess && response.data != null) {
        await _handleAuthSuccess(response.data!);
        return true;
      } else {
        _handleAuthError(response.message);
        return false;
      }
    } catch (e) {
      _handleAuthError('회원가입 중 오류가 발생했습니다: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<bool> loginWithGoogle() async {
    try {
      _setLoading(true);
      
      final GoogleSignInAccount? googleAccount = await _googleSignIn.signIn();
      if (googleAccount == null) {
        return false;
      }
      
      final GoogleSignInAuthentication googleAuth = await googleAccount.authentication;
      
      final response = await _apiService.login(LoginRequest(
        email: googleAccount.email,
        password: '', // Social login doesn't use password
      ));
      
      if (response.isSuccess && response.data != null) {
        await _handleAuthSuccess(response.data!);
        return true;
      } else {
        _handleAuthError('구글 로그인에 실패했습니다.');
        return false;
      }
    } catch (e) {
      _handleAuthError('구글 로그인 중 오류가 발생했습니다: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<bool> loginWithKakao() async {
    try {
      _setLoading(true);
      
      OAuthToken token;
      
      if (await isKakaoTalkInstalled()) {
        token = await UserApi.instance.loginWithKakaoTalk();
      } else {
        token = await UserApi.instance.loginWithKakaoAccount();
      }
      
      final kakaoUser = await UserApi.instance.me();
      
      final response = await _apiService.login(LoginRequest(
        email: kakaoUser.kakaoAccount?.email ?? '',
        password: '', // Social login doesn't use password
      ));
      
      if (response.isSuccess && response.data != null) {
        await _handleAuthSuccess(response.data!);
        return true;
      } else {
        _handleAuthError('카카오 로그인에 실패했습니다.');
        return false;
      }
    } catch (e) {
      _handleAuthError('카카오 로그인 중 오류가 발생했습니다: ${e.toString()}');
      return false;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<void> logout() async {
    try {
      _setLoading(true);
      
      try {
        await _apiService.logout();
      } catch (e) {
        print('Server logout error: $e');
      }
      
      await _googleSignIn.signOut();
      
      try {
        await UserApi.instance.logout();
      } catch (e) {
        print('Kakao logout error: $e');
      }
      
      await _clearStoredAuth();
      
    } catch (e) {
      print('Logout error: $e');
    } finally {
      _setLoading(false);
    }
  }
  
  Future<bool> refreshToken() async {
    if (_refreshToken == null) return false;
    
    try {
      final request = RefreshTokenRequest(refreshToken: _refreshToken!);
      final response = await _apiService.refreshToken(request);
      
      if (response.isSuccess && response.data != null) {
        await _handleAuthSuccess(response.data!);
        return true;
      } else {
        await _clearStoredAuth();
        return false;
      }
    } catch (e) {
      print('Token refresh error: $e');
      await _clearStoredAuth();
      return false;
    }
  }
  
  Future<User?> updateProfile({String? name, String? phone, String? profileImage}) async {
    if (!isAuthenticated) return null;
    
    try {
      _setLoading(true);
      
      final request = UpdateProfileRequest(
        name: name,
        phone: phone,
        profileImage: profileImage,
      );
      
      final response = await _apiService.updateProfile(request);
      
      if (response.isSuccess && response.data != null) {
        _user = response.data!;
        await _saveUserToStorage();
        notifyListeners();
        return _user;
      } else {
        _handleAuthError(response.message);
        return null;
      }
    } catch (e) {
      _handleAuthError('프로필 업데이트 중 오류가 발생했습니다: ${e.toString()}');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<void> _handleAuthSuccess(AuthResponse authResponse) async {
    _user = authResponse.user;
    _accessToken = authResponse.accessToken;
    _refreshToken = authResponse.refreshToken;
    _isAuthenticated = true;
    
    await _saveAuthToStorage();
    notifyListeners();
  }
  
  void _handleAuthError(String message) {
    print('Auth error: $message');
  }
  
  Future<void> _saveAuthToStorage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      if (_accessToken != null) {
        await prefs.setString(AppConstants.keyAccessToken, _accessToken!);
      }
      
      if (_refreshToken != null) {
        await prefs.setString(AppConstants.keyRefreshToken, _refreshToken!);
      }
      
      await _saveUserToStorage();
    } catch (e) {
      print('Error saving auth to storage: $e');
    }
  }
  
  Future<void> _saveUserToStorage() async {
    if (_user == null) return;
    
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(AppConstants.keyUserData, _user!.toJson().toString());
    } catch (e) {
      print('Error saving user to storage: $e');
    }
  }
  
  Future<void> _clearStoredAuth() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(AppConstants.keyAccessToken);
      await prefs.remove(AppConstants.keyRefreshToken);
      await prefs.remove(AppConstants.keyUserData);
      
      _user = null;
      _accessToken = null;
      _refreshToken = null;
      _isAuthenticated = false;
      
      notifyListeners();
    } catch (e) {
      print('Error clearing stored auth: $e');
    }
  }
  
  Future<void> _validateAndRefreshToken() async {
    if (_accessToken == null) return;
    
    try {
      final response = await _apiService.getProfile();
      if (!response.isSuccess) {
        if (response.statusCode == 401) {
          final refreshSuccess = await refreshToken();
          if (!refreshSuccess) {
            await _clearStoredAuth();
          }
        }
      }
    } catch (e) {
      print('Token validation error: $e');
      final refreshSuccess = await refreshToken();
      if (!refreshSuccess) {
        await _clearStoredAuth();
      }
    }
  }
  
  Future<Map<String, dynamic>> _parseUserData(String userData) async {
    try {
      return Map<String, dynamic>.from(
        userData as Map,
      );
    } catch (e) {
      throw Exception('Failed to parse user data');
    }
  }
  
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
}