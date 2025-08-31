import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../utils/constants.dart';

class NotificationService extends ChangeNotifier {
  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications = 
      FlutterLocalNotificationsPlugin();
  
  String? _fcmToken;
  bool _isInitialized = false;
  bool _permissionGranted = false;
  NotificationSettings? _notificationSettings;
  
  String? get fcmToken => _fcmToken;
  bool get isInitialized => _isInitialized;
  bool get permissionGranted => _permissionGranted;
  NotificationSettings? get notificationSettings => _notificationSettings;
  
  Future<void> initialize() async {
    try {
      await _initializeLocalNotifications();
      await _initializeFirebaseMessaging();
      await _setupMessageHandlers();
      _isInitialized = true;
      notifyListeners();
    } catch (e) {
      print('Error initializing notifications: $e');
    }
  }
  
  Future<void> _initializeLocalNotifications() async {
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    
    const initializationSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    
    await _localNotifications.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: _onNotificationResponse,
    );
    
    if (Platform.isAndroid) {
      await _createNotificationChannel();
    }
  }
  
  Future<void> _initializeFirebaseMessaging() async {
    _notificationSettings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );
    
    _permissionGranted = _notificationSettings?.authorizationStatus == 
        AuthorizationStatus.authorized ||
        _notificationSettings?.authorizationStatus == 
        AuthorizationStatus.provisional;
    
    if (_permissionGranted) {
      _fcmToken = await _firebaseMessaging.getToken();
      print('FCM Token: $_fcmToken');
      
      await _saveFcmToken(_fcmToken);
    }
    
    _firebaseMessaging.onTokenRefresh.listen((token) async {
      _fcmToken = token;
      await _saveFcmToken(token);
      print('FCM Token refreshed: $token');
      notifyListeners();
    });
  }
  
  Future<void> _setupMessageHandlers() async {
    FirebaseMessaging.onMessage.listen(_onForegroundMessage);
    FirebaseMessaging.onMessageOpenedApp.listen(_onMessageOpenedApp);
    
    final initialMessage = await _firebaseMessaging.getInitialMessage();
    if (initialMessage != null) {
      _onMessageOpenedApp(initialMessage);
    }
  }
  
  Future<bool> requestPermission() async {
    try {
      if (Platform.isIOS) {
        final settings = await _firebaseMessaging.requestPermission(
          alert: true,
          badge: true,
          sound: true,
        );
        
        _permissionGranted = settings.authorizationStatus == 
            AuthorizationStatus.authorized ||
            settings.authorizationStatus == AuthorizationStatus.provisional;
      } else {
        final status = await Permission.notification.request();
        _permissionGranted = status.isGranted;
      }
      
      if (_permissionGranted && _fcmToken == null) {
        _fcmToken = await _firebaseMessaging.getToken();
        await _saveFcmToken(_fcmToken);
      }
      
      notifyListeners();
      return _permissionGranted;
    } catch (e) {
      print('Error requesting notification permission: $e');
      return false;
    }
  }
  
  Future<void> showLocalNotification({
    required String title,
    required String body,
    String? payload,
    NotificationCategory category = NotificationCategory.general,
  }) async {
    if (!_permissionGranted) return;
    
    try {
      final androidDetails = AndroidNotificationDetails(
        AppConstants.notificationChannelId,
        AppConstants.notificationChannelName,
        channelDescription: AppConstants.notificationChannelDescription,
        importance: Importance.high,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
        color: AppConstants.primaryColor,
        category: _getAndroidCategory(category),
      );
      
      const iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      );
      
      const notificationDetails = NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      );
      
      await _localNotifications.show(
        DateTime.now().millisecondsSinceEpoch.remainder(100000),
        title,
        body,
        notificationDetails,
        payload: payload,
      );
    } catch (e) {
      print('Error showing local notification: $e');
    }
  }
  
  Future<void> showScheduledNotification({
    required String title,
    required String body,
    required DateTime scheduledDate,
    String? payload,
    NotificationCategory category = NotificationCategory.general,
  }) async {
    if (!_permissionGranted) return;
    
    try {
      final androidDetails = AndroidNotificationDetails(
        AppConstants.notificationChannelId,
        AppConstants.notificationChannelName,
        channelDescription: AppConstants.notificationChannelDescription,
        importance: Importance.high,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
        color: AppConstants.primaryColor,
        category: _getAndroidCategory(category),
      );
      
      const iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      );
      
      const notificationDetails = NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      );
      
      await _localNotifications.zonedSchedule(
        DateTime.now().millisecondsSinceEpoch.remainder(100000),
        title,
        body,
        scheduledDate,
        notificationDetails,
        payload: payload,
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        uiLocalNotificationDateInterpretation:
            UILocalNotificationDateInterpretation.absoluteTime,
      );
    } catch (e) {
      print('Error showing scheduled notification: $e');
    }
  }
  
  Future<void> cancelNotification(int id) async {
    await _localNotifications.cancel(id);
  }
  
  Future<void> cancelAllNotifications() async {
    await _localNotifications.cancelAll();
  }
  
  Future<void> subscribeToTopic(String topic) async {
    if (!_permissionGranted) return;
    
    try {
      await _firebaseMessaging.subscribeToTopic(topic);
      print('Subscribed to topic: $topic');
    } catch (e) {
      print('Error subscribing to topic $topic: $e');
    }
  }
  
  Future<void> unsubscribeFromTopic(String topic) async {
    try {
      await _firebaseMessaging.unsubscribeFromTopic(topic);
      print('Unsubscribed from topic: $topic');
    } catch (e) {
      print('Error unsubscribing from topic $topic: $e');
    }
  }
  
  Future<void> _onForegroundMessage(RemoteMessage message) async {
    print('Received foreground message: ${message.messageId}');
    
    await showLocalNotification(
      title: message.notification?.title ?? '알림',
      body: message.notification?.body ?? '새로운 알림이 있습니다.',
      payload: message.data.toString(),
      category: _getCategoryFromData(message.data),
    );
  }
  
  void _onMessageOpenedApp(RemoteMessage message) {
    print('Message opened app: ${message.messageId}');
    _handleNotificationTap(message.data);
  }
  
  void _onNotificationResponse(NotificationResponse response) {
    if (response.payload != null) {
      print('Notification tapped with payload: ${response.payload}');
    }
  }
  
  void _handleNotificationTap(Map<String, dynamic> data) {
    final type = data['type'] as String?;
    final academyId = data['academy_id'] as String?;
    final url = data['url'] as String?;
    
    switch (type) {
      case 'academy_promotion':
        if (academyId != null) {
          print('Navigate to academy: $academyId');
        }
        break;
      case 'system_notice':
        print('Show system notice');
        break;
      case 'inquiry_response':
        print('Navigate to inquiries');
        break;
      default:
        if (url != null) {
          print('Navigate to URL: $url');
        }
    }
  }
  
  Future<void> _createNotificationChannel() async {
    const androidChannel = AndroidNotificationChannel(
      AppConstants.notificationChannelId,
      AppConstants.notificationChannelName,
      description: AppConstants.notificationChannelDescription,
      importance: Importance.high,
    );
    
    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(androidChannel);
  }
  
  AndroidNotificationCategory _getAndroidCategory(NotificationCategory category) {
    switch (category) {
      case NotificationCategory.academy:
        return AndroidNotificationCategory.reminder;
      case NotificationCategory.promotion:
        return AndroidNotificationCategory.promo;
      case NotificationCategory.inquiry:
        return AndroidNotificationCategory.message;
      case NotificationCategory.system:
        return AndroidNotificationCategory.service;
      default:
        return AndroidNotificationCategory.recommendation;
    }
  }
  
  NotificationCategory _getCategoryFromData(Map<String, dynamic> data) {
    final type = data['type'] as String?;
    switch (type) {
      case 'academy_promotion':
        return NotificationCategory.promotion;
      case 'inquiry_response':
        return NotificationCategory.inquiry;
      case 'system_notice':
        return NotificationCategory.system;
      default:
        return NotificationCategory.general;
    }
  }
  
  Future<void> _saveFcmToken(String? token) async {
    if (token == null) return;
    
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', token);
    } catch (e) {
      print('Error saving FCM token: $e');
    }
  }
  
  Future<String?> getSavedFcmToken() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString('fcm_token');
    } catch (e) {
      print('Error getting saved FCM token: $e');
      return null;
    }
  }
}

enum NotificationCategory {
  general,
  academy,
  promotion,
  inquiry,
  system,
}

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  print('Background message: ${message.messageId}');
}