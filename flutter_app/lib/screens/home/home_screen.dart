import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:shimmer/shimmer.dart';
import 'package:go_router/go_router.dart';

import '../../services/auth_service.dart';
import '../../services/location_service.dart';
import '../../repositories/academy_repository.dart';
import '../../models/academy.dart';
import '../../utils/constants.dart';
import '../../widgets/academy_card.dart';
import '../../widgets/search_bar_widget.dart';
import '../../widgets/category_chips.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/error_widget.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ScrollController _scrollController = ScrollController();
  List<Academy> _nearbyAcademies = [];
  List<Academy> _popularAcademies = [];
  bool _isLoading = true;
  String? _error;
  String _selectedCategory = '전체';

  @override
  void initState() {
    super.initState();
    _loadInitialData();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadInitialData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await Future.wait([
        _loadNearbyAcademies(),
        _loadPopularAcademies(),
      ]);
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _loadNearbyAcademies() async {
    try {
      final locationService = context.read<LocationService>();
      final academyRepository = context.read<AcademyRepository>();

      if (locationService.hasLocation) {
        final academies = await academyRepository.getNearbyAcademies(
          latitude: locationService.latitude,
          longitude: locationService.longitude,
          radius: 5.0,
          limit: 10,
        );

        if (mounted) {
          setState(() {
            _nearbyAcademies = academies;
          });
        }
      }
    } catch (e) {
      print('Error loading nearby academies: $e');
    }
  }

  Future<void> _loadPopularAcademies() async {
    try {
      final academyRepository = context.read<AcademyRepository>();
      final academies = await academyRepository.getAcademies(
        page: 1,
        pageSize: 10,
        ordering: 'rating',
      );

      if (mounted) {
        setState(() {
          _popularAcademies = academies.results;
        });
      }
    } catch (e) {
      print('Error loading popular academies: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authService = context.watch<AuthService>();
    final locationService = context.watch<LocationService>();

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadInitialData,
          child: _isLoading
              ? const Center(child: LoadingIndicator())
              : _error != null
                  ? Center(
                      child: CustomErrorWidget(
                        message: _error!,
                        onRetry: _loadInitialData,
                      ),
                    )
                  : CustomScrollView(
                      controller: _scrollController,
                      slivers: [
                        _buildHeader(theme, authService, locationService),
                        _buildSearchSection(),
                        _buildCategorySection(),
                        if (_nearbyAcademies.isNotEmpty) _buildNearbySection(),
                        _buildPopularSection(),
                      ],
                    ),
        ),
      ),
    );
  }

  Widget _buildHeader(
    ThemeData theme,
    AuthService authService,
    LocationService locationService,
  ) {
    return SliverToBoxAdapter(
      child: Container(
        padding: const EdgeInsets.all(AppConstants.paddingMedium),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppConstants.primaryColor,
              AppConstants.primaryColor.withOpacity(0.8),
            ],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        authService.isAuthenticated
                            ? '안녕하세요, ${authService.user?.name ?? '사용자'}님!'
                            : '안녕하세요!',
                        style: theme.textTheme.headlineSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: AppConstants.paddingSmall),
                      Text(
                        locationService.hasLocation
                            ? locationService.currentAddress ?? '위치 정보 없음'
                            : '위치 서비스를 활성화해주세요',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: Colors.white.withOpacity(0.9),
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.notifications_outlined),
                  color: Colors.white,
                  onPressed: () {
                    // TODO: Navigate to notifications
                  },
                ),
              ],
            ),
            const SizedBox(height: AppConstants.paddingLarge),
            _buildQuickStats(),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickStats() {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            icon: Icons.school,
            title: '근처 학원',
            value: '${_nearbyAcademies.length}개',
          ),
        ),
        const SizedBox(width: AppConstants.paddingMedium),
        Expanded(
          child: _buildStatCard(
            icon: Icons.favorite,
            title: '즐겨찾기',
            value: '0개', // TODO: Get from user data
          ),
        ),
        const SizedBox(width: AppConstants.paddingMedium),
        Expanded(
          child: _buildStatCard(
            icon: Icons.history,
            title: '최근 검색',
            value: '0개', // TODO: Get from search history
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String title,
    required String value,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppConstants.paddingMedium),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.15),
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
      ),
      child: Column(
        children: [
          Icon(icon, color: Colors.white, size: 24),
          const SizedBox(height: AppConstants.paddingSmall),
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchSection() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.paddingMedium),
        child: SearchBarWidget(
          onTap: () => context.go('/search'),
          onChanged: (query) {},
          readOnly: true,
        ),
      ),
    );
  }

  Widget _buildCategorySection() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppConstants.paddingMedium,
        ),
        child: CategoryChips(
          categories: AppConstants.subjectFilters,
          selectedCategory: _selectedCategory,
          onCategorySelected: (category) {
            setState(() {
              _selectedCategory = category;
            });
            // TODO: Filter academies by category
          },
        ),
      ),
    );
  }

  Widget _buildNearbySection() {
    return SliverToBoxAdapter(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(AppConstants.paddingMedium),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '내 주변 학원',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton(
                  onPressed: () => context.go('/map'),
                  child: const Text('더보기'),
                ),
              ],
            ),
          ),
          SizedBox(
            height: 280,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(
                horizontal: AppConstants.paddingMedium,
              ),
              itemCount: _nearbyAcademies.length,
              itemBuilder: (context, index) {
                final academy = _nearbyAcademies[index];
                return Container(
                  width: 250,
                  margin: const EdgeInsets.only(
                    right: AppConstants.paddingMedium,
                  ),
                  child: AcademyCard(
                    academy: academy,
                    onTap: () => context.push('/home/academy/${academy.id}'),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPopularSection() {
    return SliverToBoxAdapter(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(AppConstants.paddingMedium),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '인기 학원',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton(
                  onPressed: () => context.go('/search'),
                  child: const Text('더보기'),
                ),
              ],
            ),
          ),
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(
              horizontal: AppConstants.paddingMedium,
            ),
            itemCount: _popularAcademies.length,
            itemBuilder: (context, index) {
              final academy = _popularAcademies[index];
              return Padding(
                padding: const EdgeInsets.only(
                  bottom: AppConstants.paddingMedium,
                ),
                child: AcademyCard(
                  academy: academy,
                  onTap: () => context.push('/home/academy/${academy.id}'),
                  showRanking: true,
                  ranking: index + 1,
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}