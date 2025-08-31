import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import 'services/api_service.dart';
import 'services/location_service.dart';
import 'services/auth_service.dart';
import 'services/notification_service.dart';
import 'utils/app_router.dart';
import 'utils/theme.dart';
import 'utils/constants.dart';
import 'repositories/academy_repository.dart';
import 'repositories/user_repository.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Firebase 초기화
  await Firebase.initializeApp();
  
  // Hive 초기화
  await Hive.initFlutter();
  
  // 시스템 UI 설정
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      systemNavigationBarColor: Colors.white,
      systemNavigationBarIconBrightness: Brightness.dark,
    ),
  );
  
  // 화면 방향 제한 (세로 모드만)
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  
  runApp(const AcademyMapApp());
}

class AcademyMapApp extends StatelessWidget {
  const AcademyMapApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // 서비스 제공자들
        Provider<ApiService>(
          create: (_) => ApiService(baseUrl: AppConstants.apiBaseUrl),
        ),
        Provider<LocationService>(
          create: (_) => LocationService(),
        ),
        ChangeNotifierProvider<AuthService>(
          create: (_) => AuthService(),
        ),
        Provider<NotificationService>(
          create: (_) => NotificationService(),
        ),
        
        // 저장소 제공자들
        ProxyProvider<ApiService, AcademyRepository>(
          update: (context, apiService, _) => AcademyRepository(apiService),
        ),
        ProxyProvider<ApiService, UserRepository>(
          update: (context, apiService, _) => UserRepository(apiService),
        ),
      ],
      child: Consumer<AuthService>(
        builder: (context, authService, child) {
          return MaterialApp.router(
            title: 'AcademyMap',
            debugShowCheckedModeBanner: false,
            
            // 테마 설정
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: ThemeMode.system,
            
            // 라우터 설정
            routerConfig: AppRouter.router,
            
            // 로케일 설정
            locale: const Locale('ko', 'KR'),
            supportedLocales: const [
              Locale('ko', 'KR'),
              Locale('en', 'US'),
            ],
            
            // 스크롤 동작 설정
            scrollBehavior: const MaterialScrollBehavior().copyWith(
              dragDevices: {
                PointerDeviceKind.mouse,
                PointerDeviceKind.touch,
                PointerDeviceKind.stylus,
                PointerDeviceKind.unknown,
              },
            ),
          );
        },
      ),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({Key? key}) : super(key: key);

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
    ));
    
    _scaleAnimation = Tween<double>(
      begin: 0.8,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: const Interval(0.0, 0.7, curve: Curves.elasticOut),
    ));
    
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    _animationController.forward();
    
    // 초기화 작업들
    await Future.wait([
      _initializeServices(),
      _checkPermissions(),
      _loadUserData(),
      // 최소 스플래시 시간 보장
      Future.delayed(const Duration(milliseconds: 2500)),
    ]);
    
    // 메인 화면으로 이동
    if (mounted) {
      context.go('/home');
    }
  }

  Future<void> _initializeServices() async {
    try {
      final notificationService = context.read<NotificationService>();
      await notificationService.initialize();
      
      final locationService = context.read<LocationService>();
      await locationService.initialize();
      
    } catch (e) {
      print('서비스 초기화 오류: $e');
    }
  }

  Future<void> _checkPermissions() async {
    try {
      final locationService = context.read<LocationService>();
      await locationService.requestLocationPermission();
      
      final notificationService = context.read<NotificationService>();
      await notificationService.requestPermission();
      
    } catch (e) {
      print('권한 요청 오류: $e');
    }
  }

  Future<void> _loadUserData() async {
    try {
      final authService = context.read<AuthService>();
      await authService.loadUserFromStorage();
      
    } catch (e) {
      print('사용자 데이터 로드 오류: $e');
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Center(
        child: AnimatedBuilder(
          animation: _animationController,
          builder: (context, child) {
            return FadeTransition(
              opacity: _fadeAnimation,
              child: ScaleTransition(
                scale: _scaleAnimation,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // 로고
                    Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        color: AppConstants.primaryColor,
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: [
                          BoxShadow(
                            color: AppConstants.primaryColor.withOpacity(0.3),
                            blurRadius: 20,
                            offset: const Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.school,
                        size: 60,
                        color: Colors.white,
                      ),
                    ),
                    
                    const SizedBox(height: 32),
                    
                    // 앱 이름
                    Text(
                      'AcademyMap',
                      style: GoogleFonts.notoSans(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: AppConstants.primaryColor,
                      ),
                    ),
                    
                    const SizedBox(height: 8),
                    
                    // 부제목
                    Text(
                      '전국 학원 정보 검색',
                      style: GoogleFonts.notoSans(
                        fontSize: 16,
                        color: Colors.grey[600],
                      ),
                    ),
                    
                    const SizedBox(height: 48),
                    
                    // 로딩 인디케이터
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          AppConstants.primaryColor,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}