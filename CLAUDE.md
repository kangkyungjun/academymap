# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AcademyMap is a comprehensive Django web application for mapping and searching educational academies (학원) in Korea. It provides a multi-platform solution with web interface, REST APIs, real-time features, AI recommendations, and performance monitoring.

## Development Principles

1. **Preserve Core Functionality**: Never damage or break basic existing features unless explicitly instructed to do so
2. **Map Implementation Priority**: Pay special attention to proper map functionality and integration - this is the core feature of the application

## Architecture

### Django Apps Structure
- **main/**: Core application with academy data models, views, templates, and performance monitoring
  - Primary model: `Data` (academy information with Korean field names)
  - Performance services: caching, monitoring, database optimization
  - Management commands: `optimize_performance`, `setup_seo`
- **api/**: REST API endpoints for basic operations
- **map_api/**: Dedicated map API with `Academy` model (duplicate of main Data model)
  - Provides filtered academy data for map visualization
- **accounts/**: Custom user authentication and management
- **chat/**: Real-time chat system using Django Channels and WebSockets
- **payment/**: Payment processing integration
- **ai_recommendation/**: AI-powered academy recommendation system
  - User behavior tracking and preference analysis
  - Content-based and collaborative filtering algorithms
  - Vector space modeling for academy matching
- **templates/**: HTML templates with Korean UI elements and multi-language support

### Multi-Language Support
- Supports Korean (default), English, and Chinese (Simplified)
- Translation files located in `locale/` directory
- Dynamic language switching with Django i18n framework
- Localized content management through dedicated views

### Key Data Models
**Academy Data Models** (duplicated between main.Data and map_api.Academy):
- Basic info: 상호명 (name), addresses, coordinates (경도/위도)
- Categories: 과목_* fields (subject specializations)
- Target groups: 대상_* fields (age groups served)
- Additional: ratings, fees, shuttle service, contact info

**AI Recommendation Models**:
- UserPreference: User filtering and academy preferences
- UserBehavior: Real-time user interaction tracking
- AcademyVector: Vector representations for similarity calculations
- Recommendation: Generated recommendations with scores

## Development Commands

### Server Management
```bash
python manage.py runserver  # Development server on 127.0.0.1:8000
```

### Database Operations
```bash
python manage.py makemigrations           # Create migration files
python manage.py makemigrations app_name  # Create migrations for specific app
python manage.py migrate                  # Apply migrations
python manage.py createsuperuser          # Create admin user
```

### Performance Management
```bash
python manage.py optimize_performance --action all --verbose    # Complete performance optimization
python manage.py optimize_performance --action status          # Check system status
python manage.py optimize_performance --action cache           # Optimize cache system
python manage.py optimize_performance --action database        # Optimize database
python manage.py optimize_performance --action indexes         # Create database indexes
python manage.py optimize_performance --action analyze         # Performance analysis
python manage.py optimize_performance --action warmup          # Cache warm-up
```

### SEO Management
```bash
python manage.py setup_seo  # Initialize SEO optimizations
```

### Multi-Language Support
```bash
python manage.py makemessages -l en     # Generate English translation files
python manage.py makemessages -l zh_Hans # Generate Chinese translation files
python manage.py compilemessages        # Compile translation files
```

### Testing
```bash
python manage.py test                    # Run all tests
python manage.py test main              # Test specific app
python manage.py test ai_recommendation # Test AI recommendation system
```

## Configuration Notes

### Settings (academymap/settings.py)
- **Language/Timezone**: Korean locale (`ko`, `Asia/Seoul`) with multi-language support
- **Database**: SQLite for development
- **CORS**: Enabled for all origins (development setup)
- **Debug**: Currently enabled (change for production)  
- **Static Files**: Located in `main/static/`
- **Caching**: Local memory cache with performance optimization
- **Channels**: Redis channel layer for real-time chat (127.0.0.1:6379)
- **Performance Monitoring**: Comprehensive middleware stack for optimization

### Security Considerations
- SECRET_KEY is exposed in settings.py (needs environment variable)
- DEBUG=True in production settings
- CORS_ALLOW_ALL_ORIGINS=True (should be restricted)

### Key URL Patterns
**User Interface (i18n supported)**:
- `/`: Map view (primary interface)
- `/search`: Academy search with filters
- `/academy/<id>`: Individual academy details
- `/enhanced-academy/<id>/`: Enhanced academy details with social features
- `/manage/`: Academy management interface
- `/operator/dashboard/`: Operator management dashboard
- `/performance/`: Performance monitoring dashboard
- `/analytics/`: Data analytics and reporting
- `/seo/`: SEO management interface

**API Endpoints (language independent)**:
- `/api/v1/`: Basic REST API endpoints
- `/api/enhanced/`: Enhanced DRF API with analytics
- `/map_api/`: Dedicated map data API
- `/ai-recommendation/`: AI recommendation system API
- `/chat/`: Real-time chat WebSocket endpoints
- `/payment/`: Payment processing API
- `/performance/metrics/`: Performance monitoring API
- `/performance/cache/`: Cache management API
- `/performance/database/`: Database optimization API

## Advanced Systems

### Performance Optimization
**Cache System Architecture**:
- Multi-layer caching: AcademyCacheService, SearchCacheService, StatisticsCacheService
- Automatic cache warming and invalidation
- Performance monitoring with real-time metrics

**Database Optimization**:
- Automatic index creation for frequently queried fields
- N+1 query detection and prevention
- Slow query analysis and optimization recommendations

**Middleware Stack** (in order):
1. SecurityHeadersMiddleware - Security headers injection
2. PerformanceMonitoringMiddleware - Request/response time tracking
3. CompressionMiddleware - Response compression
4. CacheMiddleware - Page-level caching (after authentication)
5. DatabaseOptimizationMiddleware - Query optimization monitoring
6. ResponseOptimizationMiddleware - ETag and cache control headers

### AI Recommendation System
**Core Services**:
- `PreferenceAnalyzer`: User preference analysis from behavior
- `VectorBuilder`: Academy feature vectorization using TF-IDF
- `SimilarityCalculator`: Cosine similarity calculations
- `RecommendationEngine`: Hybrid content-based and collaborative filtering

**Real-time Behavior Tracking**:
- User interactions (views, searches, filters) stored for analysis
- Preference weights automatically adjusted based on behavior patterns
- Academy similarity calculations for collaborative filtering

### Real-time Features
**Chat System**:
- WebSocket connections using Django Channels
- Real-time messaging between users and academy operators
- Message history and user management

## Data Management

### Academy Data Import
- `data_update` view handles bulk Excel data import
- File: `n_data.xlsx` contains academy data
- Korean field names throughout the schema

### Model Duplication
The codebase has two identical academy models (`main.Data` and `map_api.Academy`). This appears to be intentional for API separation but creates maintenance overhead.

### Translation Management
- Translation files in `locale/en/LC_MESSAGES/django.po` and `locale/zh_Hans/LC_MESSAGES/django.po`
- Dynamic language detection and content localization
- Language-specific URL patterns with i18n_patterns

## Frontend Integration

### Multi-Platform Support
- **Web Interface**: Django templates with Bootstrap 5, Korean/English/Chinese support
- **Flutter App**: Cross-platform mobile application in `academymap_flutter/`
- **REST APIs**: Comprehensive API endpoints for mobile and third-party integration

### Key Features
- Real-time academy filtering by location, price, subjects, age groups
- Map-based visualization with markers
- Academy management CRUD operations
- Bulk data upload functionality
- AI-powered academy recommendations
- Real-time chat system
- Performance monitoring dashboard
- Multi-language content management
- Social media integration and sharing
- SEO optimization with dynamic sitemaps