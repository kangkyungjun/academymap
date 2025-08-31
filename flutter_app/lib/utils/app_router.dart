import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../main.dart';
import '../screens/home/home_screen.dart';
import '../screens/search/search_screen.dart';
import '../screens/map/map_screen.dart';
import '../screens/favorites/favorites_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/academy/academy_detail_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/auth/forgot_password_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../screens/settings/notification_settings_screen.dart';
import '../screens/settings/privacy_settings_screen.dart';
import '../screens/settings/about_screen.dart';
import '../screens/onboarding/onboarding_screen.dart';
import '../screens/error/error_screen.dart';
import '../services/auth_service.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: '/splash',
    debugLogDiagnostics: true,
    redirect: _handleRedirect,
    routes: [
      // Splash Screen
      GoRoute(
        path: '/splash',
        name: 'splash',
        builder: (context, state) => const SplashScreen(),
      ),
      
      // Onboarding
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      
      // Authentication Routes
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/forgot-password',
        name: 'forgot-password',
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      
      // Main App Shell with Bottom Navigation
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => 
            MainNavigationShell(navigationShell: navigationShell),
        branches: [
          // Home Tab
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/home',
                name: 'home',
                builder: (context, state) => const HomeScreen(),
                routes: [
                  GoRoute(
                    path: 'academy/:id',
                    name: 'academy-detail',
                    builder: (context, state) {
                      final academyId = int.parse(state.pathParameters['id']!);
                      return AcademyDetailScreen(academyId: academyId);
                    },
                  ),
                ],
              ),
            ],
          ),
          
          // Search Tab
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/search',
                name: 'search',
                builder: (context, state) => const SearchScreen(),
              ),
            ],
          ),
          
          // Map Tab
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/map',
                name: 'map',
                builder: (context, state) => const MapScreen(),
              ),
            ],
          ),
          
          // Favorites Tab
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/favorites',
                name: 'favorites',
                builder: (context, state) => const FavoritesScreen(),
              ),
            ],
          ),
          
          // Profile Tab
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                name: 'profile',
                builder: (context, state) => const ProfileScreen(),
                routes: [
                  GoRoute(
                    path: 'settings',
                    name: 'settings',
                    builder: (context, state) => const SettingsScreen(),
                    routes: [
                      GoRoute(
                        path: 'notifications',
                        name: 'notification-settings',
                        builder: (context, state) => const NotificationSettingsScreen(),
                      ),
                      GoRoute(
                        path: 'privacy',
                        name: 'privacy-settings',
                        builder: (context, state) => const PrivacySettingsScreen(),
                      ),
                      GoRoute(
                        path: 'about',
                        name: 'about',
                        builder: (context, state) => const AboutScreen(),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
      
      // Error Routes
      GoRoute(
        path: '/error',
        name: 'error',
        builder: (context, state) => ErrorScreen(
          error: state.extra as String?,
        ),
      ),
    ],
    
    errorBuilder: (context, state) => ErrorScreen(
      error: state.error?.toString(),
    ),
  );
  
  static String? _handleRedirect(BuildContext context, GoRouterState state) {
    final authService = context.read<AuthService>();
    final isAuthenticated = authService.isAuthenticated;
    final currentLocation = state.uri.toString();
    
    // If on splash screen, let it handle its own navigation
    if (currentLocation == '/splash') {
      return null;
    }
    
    // Authentication flow
    final authRoutes = ['/login', '/register', '/forgot-password'];
    final publicRoutes = ['/onboarding', '/error'];
    final isAuthRoute = authRoutes.contains(currentLocation);
    final isPublicRoute = publicRoutes.contains(currentLocation);
    
    // If user is authenticated and on auth route, redirect to home
    if (isAuthenticated && isAuthRoute) {
      return '/home';
    }
    
    // If user is not authenticated and not on public/auth route, redirect to login
    if (!isAuthenticated && !isAuthRoute && !isPublicRoute) {
      return '/login';
    }
    
    return null; // No redirect needed
  }
}

class MainNavigationShell extends StatelessWidget {
  final StatefulNavigationShell navigationShell;
  
  const MainNavigationShell({
    Key? key,
    required this.navigationShell,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: navigationShell.currentIndex,
        onTap: (index) => navigationShell.goBranch(
          index,
          initialLocation: index == navigationShell.currentIndex,
        ),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: '홈',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.search),
            label: '검색',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.map),
            label: '지도',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.favorite),
            label: '즐겨찾기',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: '프로필',
          ),
        ],
      ),
    );
  }
}

// Navigation Extensions
extension GoRouterExtension on GoRouter {
  void pushAndClearStack(String location) {
    while (canPop()) {
      pop();
    }
    go(location);
  }
}

extension BuildContextExtension on BuildContext {
  void showErrorSnackBar(String message) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(this).colorScheme.error,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
  
  void showSuccessSnackBar(String message) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(this).colorScheme.primary,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
  
  void showLoadingDialog() {
    showDialog(
      context: this,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
  
  void hideLoadingDialog() {
    Navigator.of(this).pop();
  }
}