// AcademyMap Flutter 앱 테스트

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:academymap_flutter/main.dart';

void main() {
  group('AcademyMap 앱 테스트', () {
    testWidgets('앱이 정상적으로 시작되는지 확인', (WidgetTester tester) async {
      // 앱 빌드 및 프레임 트리거
      await tester.pumpWidget(const AcademyMapApp());

      // 앱 제목 확인
      expect(find.text('🏫 AcademyMap'), findsOneWidget);

      // 주요 UI 요소들이 존재하는지 확인
      expect(find.byType(Scaffold), findsOneWidget);
      expect(find.byType(AppBar), findsOneWidget);
    });

    testWidgets('지도/리스트 토글 버튼이 존재하는지 확인', (WidgetTester tester) async {
      await tester.pumpWidget(const AcademyMapApp());
      await tester.pump();

      // 토글 버튼들이 존재하는지 확인
      expect(find.byType(ToggleButtons), findsOneWidget);
    });

    testWidgets('검색 필드가 존재하는지 확인', (WidgetTester tester) async {
      await tester.pumpWidget(const AcademyMapApp());
      await tester.pump();

      // 검색 관련 UI 요소 확인
      expect(find.byType(TextField), findsWidgets);
    });
  });
}