import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';
import 'package:permission_handler/permission_handler.dart';

import '../utils/constants.dart';

class LocationService extends ChangeNotifier {
  Position? _currentPosition;
  String? _currentAddress;
  bool _isLoading = false;
  bool _permissionGranted = false;
  LocationPermissionStatus _permissionStatus = LocationPermissionStatus.unknown;
  StreamSubscription<Position>? _positionStream;
  
  Position? get currentPosition => _currentPosition;
  String? get currentAddress => _currentAddress;
  bool get isLoading => _isLoading;
  bool get permissionGranted => _permissionGranted;
  LocationPermissionStatus get permissionStatus => _permissionStatus;
  bool get hasLocation => _currentPosition != null;
  
  double get latitude => _currentPosition?.latitude ?? AppConstants.defaultLatitude;
  double get longitude => _currentPosition?.longitude ?? AppConstants.defaultLongitude;
  
  Future<void> initialize() async {
    await checkPermissionStatus();
    if (_permissionGranted) {
      await getCurrentLocation();
    }
  }
  
  Future<LocationPermissionStatus> checkPermissionStatus() async {
    try {
      final permission = await Geolocator.checkPermission();
      
      switch (permission) {
        case LocationPermission.always:
        case LocationPermission.whileInUse:
          _permissionStatus = LocationPermissionStatus.granted;
          _permissionGranted = true;
          break;
        case LocationPermission.denied:
          _permissionStatus = LocationPermissionStatus.denied;
          _permissionGranted = false;
          break;
        case LocationPermission.deniedForever:
          _permissionStatus = LocationPermissionStatus.permanentlyDenied;
          _permissionGranted = false;
          break;
        case LocationPermission.unableToDetermine:
          _permissionStatus = LocationPermissionStatus.unknown;
          _permissionGranted = false;
          break;
      }
      
      notifyListeners();
      return _permissionStatus;
    } catch (e) {
      print('Error checking location permission: $e');
      _permissionStatus = LocationPermissionStatus.unknown;
      _permissionGranted = false;
      notifyListeners();
      return _permissionStatus;
    }
  }
  
  Future<bool> requestLocationPermission() async {
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw LocationServiceException('위치 서비스가 비활성화되어 있습니다.');
      }
      
      LocationPermission permission = await Geolocator.checkPermission();
      
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      
      switch (permission) {
        case LocationPermission.always:
        case LocationPermission.whileInUse:
          _permissionStatus = LocationPermissionStatus.granted;
          _permissionGranted = true;
          notifyListeners();
          return true;
        case LocationPermission.denied:
          _permissionStatus = LocationPermissionStatus.denied;
          _permissionGranted = false;
          break;
        case LocationPermission.deniedForever:
          _permissionStatus = LocationPermissionStatus.permanentlyDenied;
          _permissionGranted = false;
          break;
        case LocationPermission.unableToDetermine:
          _permissionStatus = LocationPermissionStatus.unknown;
          _permissionGranted = false;
          break;
      }
      
      notifyListeners();
      return false;
    } catch (e) {
      print('Error requesting location permission: $e');
      _permissionStatus = LocationPermissionStatus.unknown;
      _permissionGranted = false;
      notifyListeners();
      return false;
    }
  }
  
  Future<Position?> getCurrentLocation({bool forceUpdate = false}) async {
    if (!forceUpdate && _currentPosition != null) {
      return _currentPosition;
    }
    
    try {
      _setLoading(true);
      
      final hasPermission = await _ensurePermission();
      if (!hasPermission) {
        throw LocationPermissionException(AppConstants.errorLocationPermission);
      }
      
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw LocationServiceException(AppConstants.errorLocationService);
      }
      
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 15),
      );
      
      _currentPosition = position;
      await _updateAddress(position);
      
      notifyListeners();
      return position;
    } catch (e) {
      print('Error getting current location: $e');
      rethrow;
    } finally {
      _setLoading(false);
    }
  }
  
  Future<void> startLocationTracking({
    LocationAccuracy accuracy = LocationAccuracy.high,
    int distanceFilter = 10,
  }) async {
    try {
      final hasPermission = await _ensurePermission();
      if (!hasPermission) {
        throw LocationPermissionException(AppConstants.errorLocationPermission);
      }
      
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw LocationServiceException(AppConstants.errorLocationService);
      }
      
      const locationSettings = LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 10,
      );
      
      _positionStream = Geolocator.getPositionStream(
        locationSettings: locationSettings,
      ).listen(
        (Position position) {
          _currentPosition = position;
          _updateAddress(position);
          notifyListeners();
        },
        onError: (error) {
          print('Location tracking error: $error');
        },
      );
    } catch (e) {
      print('Error starting location tracking: $e');
      rethrow;
    }
  }
  
  void stopLocationTracking() {
    _positionStream?.cancel();
    _positionStream = null;
  }
  
  Future<double> getDistanceBetween({
    required double latitude1,
    required double longitude1,
    required double latitude2,
    required double longitude2,
  }) async {
    try {
      return Geolocator.distanceBetween(latitude1, longitude1, latitude2, longitude2);
    } catch (e) {
      print('Error calculating distance: $e');
      return double.infinity;
    }
  }
  
  Future<String?> getAddressFromCoordinates(double latitude, double longitude) async {
    try {
      final placemarks = await placemarkFromCoordinates(latitude, longitude);
      if (placemarks.isNotEmpty) {
        final placemark = placemarks.first;
        return _formatAddress(placemark);
      }
      return null;
    } catch (e) {
      print('Error getting address from coordinates: $e');
      return null;
    }
  }
  
  Future<List<Location>> getCoordinatesFromAddress(String address) async {
    try {
      return await locationFromAddress(address);
    } catch (e) {
      print('Error getting coordinates from address: $e');
      return [];
    }
  }
  
  Future<void> openLocationSettings() async {
    try {
      await Geolocator.openLocationSettings();
    } catch (e) {
      print('Error opening location settings: $e');
    }
  }
  
  Future<void> openAppSettings() async {
    try {
      await Geolocator.openAppSettings();
    } catch (e) {
      print('Error opening app settings: $e');
    }
  }
  
  Future<void> _updateAddress(Position position) async {
    try {
      final address = await getAddressFromCoordinates(
        position.latitude,
        position.longitude,
      );
      _currentAddress = address;
    } catch (e) {
      print('Error updating address: $e');
      _currentAddress = null;
    }
  }
  
  String _formatAddress(Placemark placemark) {
    final parts = <String>[];
    
    if (placemark.administrativeArea?.isNotEmpty ?? false) {
      parts.add(placemark.administrativeArea!);
    }
    
    if (placemark.locality?.isNotEmpty ?? false) {
      parts.add(placemark.locality!);
    }
    
    if (placemark.subLocality?.isNotEmpty ?? false) {
      parts.add(placemark.subLocality!);
    }
    
    if (placemark.thoroughfare?.isNotEmpty ?? false) {
      parts.add(placemark.thoroughfare!);
    }
    
    return parts.join(' ');
  }
  
  Future<bool> _ensurePermission() async {
    if (_permissionGranted) return true;
    
    final permissionStatus = await checkPermissionStatus();
    if (permissionStatus == LocationPermissionStatus.granted) {
      return true;
    }
    
    if (permissionStatus == LocationPermissionStatus.permanentlyDenied) {
      return false;
    }
    
    return await requestLocationPermission();
  }
  
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
  
  @override
  void dispose() {
    stopLocationTracking();
    super.dispose();
  }
}

enum LocationPermissionStatus {
  unknown,
  granted,
  denied,
  permanentlyDenied,
}

class LocationPermissionException implements Exception {
  final String message;
  LocationPermissionException(this.message);
  
  @override
  String toString() => 'LocationPermissionException: $message';
}

class LocationServiceException implements Exception {
  final String message;
  LocationServiceException(this.message);
  
  @override
  String toString() => 'LocationServiceException: $message';
}