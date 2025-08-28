# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AcademyMap is a Django web application for mapping and searching educational academies (학원) in Korea. It provides a web-based map interface to locate academies with detailed filtering capabilities and management features.

## Development Principles

1. **Preserve Core Functionality**: Never damage or break basic existing features unless explicitly instructed to do so
2. **Map Implementation Priority**: Pay special attention to proper map functionality and integration - this is the core feature of the application

## Architecture

### App Structure
- **main/**: Core application with academy data models, views, and templates
  - Primary model: `Data` (academy information with Korean field names)
  - Main views: map display, search, filtering, academy management
- **api/**: REST API endpoints (currently minimal)
- **map_api/**: Dedicated map API with `Academy` model (duplicate of main Data model)
  - Provides filtered academy data for map visualization
- **templates/**: HTML templates with Korean UI elements

### Key Models
Both `main.models.Data` and `map_api.models.Academy` contain identical academy information:
- Basic info: 상호명 (name), addresses, coordinates (경도/위도)
- Categories: 과목_* fields (subject specializations)
- Target groups: 대상_* fields (age groups served)
- Additional: ratings, fees, shuttle service, contact info

## Development Commands

### Server Management
```bash
python manage.py runserver  # Development server on 127.0.0.1:8000
```

### Database Operations
```bash
python manage.py makemigrations  # Create migration files
python manage.py migrate        # Apply migrations
python manage.py createsuperuser # Create admin user
```

### Testing
```bash
python manage.py test           # Run all tests
python manage.py test main      # Test specific app
```

## Configuration Notes

### Settings (academymap/settings.py)
- **Language/Timezone**: Korean locale (`ko`, `Asia/Seoul`)
- **Database**: SQLite for development
- **CORS**: Enabled for all origins (development setup)
- **Debug**: Currently enabled (change for production)
- **Static Files**: Located in `main/static/`

### Security Considerations
- SECRET_KEY is exposed in settings.py (needs environment variable)
- DEBUG=True in production settings
- CORS_ALLOW_ALL_ORIGINS=True (should be restricted)

### URL Patterns
- `/`: Map view (primary interface)
- `/search`: Academy search with filters
- `/academy/<id>`: Individual academy details  
- `/manage/`: Academy management interface
- `/api/` and `/map_api/`: REST API endpoints

## Data Management

### Academy Data Import
- `data_update` view handles bulk Excel data import
- File: `n_data.xlsx` contains academy data
- Korean field names throughout the schema

### Model Duplication
The codebase has two identical academy models (`main.Data` and `map_api.Academy`). This appears to be intentional for API separation but creates maintenance overhead.

## Frontend Integration

### Templates
- Korean language interface
- Map integration (likely Kakao Map or similar)
- AJAX filtering for dynamic search results
- Bootstrap/CSS styling in `main/static/`

### Key Features
- Real-time academy filtering by location, price, subjects, age groups
- Map-based visualization with markers
- Academy management CRUD operations
- Bulk data upload functionality