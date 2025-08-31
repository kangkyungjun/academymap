import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'constants.dart';

class AppTheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      
      // 색상 스키마
      colorScheme: const ColorScheme.light(
        primary: AppConstants.primaryColor,
        onPrimary: Colors.white,
        secondary: AppConstants.secondaryColor,
        onSecondary: Colors.white,
        surface: AppConstants.surfaceColor,
        onSurface: AppConstants.textPrimary,
        background: AppConstants.backgroundColor,
        onBackground: AppConstants.textPrimary,
        error: AppConstants.errorColor,
        onError: Colors.white,
      ),
      
      // 앱바 테마
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: AppConstants.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
        titleTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeXLarge,
          fontWeight: FontWeight.w600,
          color: AppConstants.textPrimary,
        ),
        iconTheme: const IconThemeData(
          color: AppConstants.textPrimary,
          size: 24,
        ),
      ),
      
      // 텍스트 테마
      textTheme: TextTheme(
        // 제목
        headlineLarge: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeHeading,
          fontWeight: FontWeight.bold,
          color: AppConstants.textPrimary,
          height: 1.2,
        ),
        headlineMedium: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeTitle,
          fontWeight: FontWeight.w600,
          color: AppConstants.textPrimary,
          height: 1.3,
        ),
        headlineSmall: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeXXLarge,
          fontWeight: FontWeight.w600,
          color: AppConstants.textPrimary,
          height: 1.3,
        ),
        
        // 본문
        titleLarge: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeXLarge,
          fontWeight: FontWeight.w500,
          color: AppConstants.textPrimary,
          height: 1.4,
        ),
        titleMedium: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeLarge,
          fontWeight: FontWeight.w500,
          color: AppConstants.textPrimary,
          height: 1.4,
        ),
        titleSmall: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          fontWeight: FontWeight.w500,
          color: AppConstants.textPrimary,
          height: 1.4,
        ),
        
        // 본문 텍스트
        bodyLarge: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeLarge,
          fontWeight: FontWeight.normal,
          color: AppConstants.textPrimary,
          height: 1.5,
        ),
        bodyMedium: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          fontWeight: FontWeight.normal,
          color: AppConstants.textPrimary,
          height: 1.5,
        ),
        bodySmall: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeSmall,
          fontWeight: FontWeight.normal,
          color: AppConstants.textSecondary,
          height: 1.5,
        ),
        
        // 라벨
        labelLarge: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          fontWeight: FontWeight.w500,
          color: AppConstants.textPrimary,
          height: 1.4,
        ),
        labelMedium: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeSmall,
          fontWeight: FontWeight.w500,
          color: AppConstants.textSecondary,
          height: 1.4,
        ),
        labelSmall: GoogleFonts.notoSans(
          fontSize: 10.0,
          fontWeight: FontWeight.w500,
          color: AppConstants.textDisabled,
          height: 1.4,
        ),
      ),
      
      // 버튼 테마
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppConstants.primaryColor,
          foregroundColor: Colors.white,
          elevation: 2,
          shadowColor: AppConstants.primaryColor.withOpacity(0.3),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.paddingLarge,
            vertical: AppConstants.paddingMedium,
          ),
          textStyle: GoogleFonts.notoSans(
            fontSize: AppConstants.fontSizeMedium,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
      
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppConstants.primaryColor,
          side: const BorderSide(
            color: AppConstants.primaryColor,
            width: 1,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.paddingLarge,
            vertical: AppConstants.paddingMedium,
          ),
          textStyle: GoogleFonts.notoSans(
            fontSize: AppConstants.fontSizeMedium,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
      
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppConstants.primaryColor,
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.paddingMedium,
            vertical: AppConstants.paddingSmall,
          ),
          textStyle: GoogleFonts.notoSans(
            fontSize: AppConstants.fontSizeMedium,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
      
      // 카드 테마
      cardTheme: const CardTheme(
        color: AppConstants.surfaceColor,
        elevation: 2,
        shadowColor: Color(0x0A000000),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(
            Radius.circular(AppConstants.borderRadius),
          ),
        ),
        margin: EdgeInsets.zero,
      ),
      
      // 입력 필드 테마
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.grey[50],
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: BorderSide(
            color: Colors.grey[300]!,
            width: 1,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: BorderSide(
            color: Colors.grey[300]!,
            width: 1,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: const BorderSide(
            color: AppConstants.primaryColor,
            width: 2,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: const BorderSide(
            color: AppConstants.errorColor,
            width: 1,
          ),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: const BorderSide(
            color: AppConstants.errorColor,
            width: 2,
          ),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppConstants.paddingMedium,
          vertical: AppConstants.paddingMedium,
        ),
        hintStyle: GoogleFonts.notoSans(
          color: AppConstants.textDisabled,
        ),
        labelStyle: GoogleFonts.notoSans(
          color: AppConstants.textSecondary,
        ),
      ),
      
      // 칩 테마
      chipTheme: ChipThemeData(
        backgroundColor: Colors.grey[100],
        selectedColor: AppConstants.primaryColor.withOpacity(0.1),
        secondarySelectedColor: AppConstants.secondaryColor.withOpacity(0.1),
        labelStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeSmall,
          fontWeight: FontWeight.w500,
        ),
        secondaryLabelStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeSmall,
          fontWeight: FontWeight.w500,
          color: AppConstants.secondaryColor,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      
      // 하단 시트 테마
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppConstants.surfaceColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppConstants.borderRadiusLarge),
          ),
        ),
        showDragHandle: true,
        dragHandleColor: Color(0xFFE2E8F0),
      ),
      
      // 다이얼로그 테마
      dialogTheme: DialogTheme(
        backgroundColor: AppConstants.surfaceColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadiusLarge),
        ),
        titleTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeXLarge,
          fontWeight: FontWeight.w600,
          color: AppConstants.textPrimary,
        ),
        contentTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          color: AppConstants.textSecondary,
          height: 1.5,
        ),
      ),
      
      // 스낵바 테마
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppConstants.textPrimary,
        contentTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          color: Colors.white,
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        ),
      ),
      
      // 탭바 테마
      tabBarTheme: TabBarTheme(
        labelColor: AppConstants.primaryColor,
        unselectedLabelColor: AppConstants.textSecondary,
        labelStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          fontWeight: FontWeight.w500,
        ),
        unselectedLabelStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          fontWeight: FontWeight.normal,
        ),
        indicator: const UnderlineTabIndicator(
          borderSide: BorderSide(
            color: AppConstants.primaryColor,
            width: 2,
          ),
        ),
      ),
      
      // 리스트 타일 테마
      listTileTheme: ListTileThemeData(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppConstants.paddingMedium,
          vertical: AppConstants.paddingSmall,
        ),
        titleTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeLarge,
          fontWeight: FontWeight.w500,
          color: AppConstants.textPrimary,
        ),
        subtitleTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeMedium,
          color: AppConstants.textSecondary,
        ),
      ),
      
      // 진행률 인디케이터 테마
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppConstants.primaryColor,
        linearTrackColor: Color(0xFFE2E8F0),
        circularTrackColor: Color(0xFFE2E8F0),
      ),
    );
  }
  
  static ThemeData get darkTheme {
    return lightTheme.copyWith(
      brightness: Brightness.dark,
      
      // 다크 모드 색상 스키마
      colorScheme: const ColorScheme.dark(
        primary: AppConstants.primaryColorLight,
        onPrimary: Colors.black,
        secondary: AppConstants.secondaryColor,
        onSecondary: Colors.black,
        surface: Color(0xFF1E293B), // Slate-800
        onSurface: Color(0xFFF1F5F9), // Slate-100
        background: Color(0xFF0F172A), // Slate-900
        onBackground: Color(0xFFF1F5F9), // Slate-100
        error: AppConstants.errorColor,
        onError: Colors.black,
      ),
      
      // 다크 모드 앱바
      appBarTheme: lightTheme.appBarTheme.copyWith(
        backgroundColor: const Color(0xFF1E293B),
        foregroundColor: const Color(0xFFF1F5F9),
        titleTextStyle: GoogleFonts.notoSans(
          fontSize: AppConstants.fontSizeXLarge,
          fontWeight: FontWeight.w600,
          color: const Color(0xFFF1F5F9),
        ),
        iconTheme: const IconThemeData(
          color: Color(0xFFF1F5F9),
          size: 24,
        ),
      ),
      
      // 다크 모드 카드
      cardTheme: lightTheme.cardTheme.copyWith(
        color: const Color(0xFF1E293B),
      ),
      
      // 다크 모드 입력 필드
      inputDecorationTheme: lightTheme.inputDecorationTheme.copyWith(
        fillColor: const Color(0xFF334155), // Slate-700
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: const BorderSide(
            color: Color(0xFF475569), // Slate-600
            width: 1,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.borderRadius),
          borderSide: const BorderSide(
            color: Color(0xFF475569), // Slate-600
            width: 1,
          ),
        ),
      ),
    );
  }
}