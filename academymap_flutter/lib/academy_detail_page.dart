import 'package:flutter/material.dart';
import 'dart:html' as html;
import 'widgets/tuition_comparison_chart.dart';

class AcademyDetailPage extends StatelessWidget {
  final Map<String, dynamic> academy;

  const AcademyDetailPage({Key? key, required this.academy}) : super(key: key);

  // 과목별 색상 반환
  Color _getSubjectColor(String subject) {
    switch (subject) {
      case '수학':
        return const Color(0xFFDC3545);
      case '영어':
        return const Color(0xFF007BFF);
      case '과학':
        return const Color(0xFF28A745);
      case '예체능':
        return const Color(0xFFFD7E14);
      case '컴퓨터':
        return const Color(0xFF17A2B8);
      case '외국어':
        return const Color(0xFF6F42C1);
      case '논술':
        return const Color(0xFF795548);
      default:
        return const Color(0xFF6C757D);
    }
  }

  // 학원의 주요 과목을 판단
  String _getPrimarySubject() {
    if (academy['과목_수학'] == true) return '수학';
    if (academy['과목_영어'] == true) return '영어';
    if (academy['과목_과학'] == true) return '과학';
    if (academy['과목_예체능'] == true) return '예체능';
    if (academy['과목_컴퓨터'] == true) return '컴퓨터';
    if (academy['과목_외국어'] == true) return '외국어';
    if (academy['과목_논술'] == true) return '논술';
    if (academy['과목_기타'] == true) return '기타';
    return '기타';
  }

  // 수강료 포맷팅 함수
  String? _formatTuition(dynamic tuition) {
    if (tuition == null || tuition == '' || tuition == 'null') {
      return null;
    }

    // 문자열인 경우 숫자로 변환 시도
    double? tuitionValue;
    if (tuition is String) {
      tuitionValue = double.tryParse(tuition.replaceAll(',', '').replaceAll('원', ''));
    } else if (tuition is num) {
      tuitionValue = tuition.toDouble();
    }

    if (tuitionValue == null || tuitionValue == 0) {
      return null;
    }

    // 천 단위 콤마 추가
    final formatter = tuitionValue.toStringAsFixed(0).replaceAllMapped(
      RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
      (Match m) => '${m[1]},'
    );
    return '$formatter원';
  }

  // 과목별 아이콘 반환
  String _getSubjectIcon(String subject) {
    switch (subject) {
      case '수학':
        return '➕';
      case '영어':
        return '📚';
      case '과학':
        return '🔬';
      case '예체능':
        return '🎨';
      case '컴퓨터':
        return '💻';
      case '외국어':
        return '🌍';
      case '논술':
        return '✏️';
      default:
        return '📖';
    }
  }

  Widget _buildInfoRow(String icon, String label, String? value) {
    // 값이 없을 때 "정보 없음" 표시
    final displayValue = (value == null || value.isEmpty || value == 'null')
        ? '정보 없음'
        : value;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(icon, style: TextStyle(fontSize: 20)),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  displayValue,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: displayValue == '정보 없음' ? Colors.grey : null,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChip(String label, Color color) {
    return Chip(
      label: Text(
        label,
        style: TextStyle(color: Colors.white, fontSize: 12),
      ),
      backgroundColor: color,
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  void _makePhoneCall(String? phoneNumber) {
    if (phoneNumber != null && phoneNumber.isNotEmpty) {
      html.window.open('tel:$phoneNumber', '_self');
    }
  }

  // 차트 표시 여부 결정 함수
  bool _shouldShowTuitionChart(dynamic tuition) {
    if (tuition == null || tuition == '' || tuition == 'null') {
      return false;
    }

    // 숫자로 변환 가능한지 확인
    double? tuitionValue;
    if (tuition is String) {
      tuitionValue = double.tryParse(tuition.replaceAll(',', '').replaceAll('원', ''));
    } else if (tuition is num) {
      tuitionValue = tuition.toDouble();
    }

    // 0보다 큰 값이 있을 때만 차트 표시
    return tuitionValue != null && tuitionValue > 0;
  }

  void _openMap(BuildContext context) {
    print('🗺️ _openMap 함수 호출됨');
    final lat = academy['위도'];
    final lng = academy['경도'];
    final name = academy['상호명'] ?? '학원';

    print('📍 학원 위치: $name - 위도: $lat, 경도: $lng');

    if (lat != null && lng != null) {
      // 메인 페이지로 돌아가면서 학원 위치 정보 전달
      print('✅ Navigator.pop 호출 - 지도 페이지로 돌아가기');
      Navigator.pop(context, {
        'lat': lat,
        'lng': lng,
        'name': name,
      });
    } else {
      print('❌ 위치 정보가 없습니다');
    }
  }

  @override
  Widget build(BuildContext context) {
    // 디버깅: 학원 데이터 확인
    print('🏫 Academy data: ${academy}');
    print('💰 수강료_평균: ${academy['수강료_평균']}');
    print('💰 수강료 타입: ${academy['수강료_평균'].runtimeType}');

    final primarySubject = _getPrimarySubject();

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // 앱바
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              title: Text(
                academy['상호명'] ?? '학원 정보',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      _getSubjectColor(primarySubject).withOpacity(0.8),
                      _getSubjectColor(primarySubject),
                    ],
                  ),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(40),
                        ),
                        child: Center(
                          child: Text(
                            _getSubjectIcon(primarySubject),
                            style: TextStyle(fontSize: 40),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // 컨텐츠
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 액션 버튼들
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _makePhoneCall(academy['전화번호']),
                          icon: Icon(Icons.phone),
                          label: Text('전화하기'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green,
                            padding: EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                      SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () => _openMap(context),
                          icon: Icon(Icons.map),
                          label: Text('지도보기'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.blue,
                            padding: EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                    ],
                  ),

                  SizedBox(height: 24),

                  // 기본 정보 섹션
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '📋 기본 정보',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 16),
                          _buildInfoRow('📍', '주소', academy['도로명주소']),
                          _buildInfoRow('📞', '전화', academy['전화번호']),
                          _buildInfoRow('⭐', '평점', academy['별점']?.toString()),
                          _buildInfoRow('💰', '수강료', _formatTuition(academy['수강료_평균'])),
                          _buildInfoRow('🕒', '영업시간', academy['영업시간']),
                          _buildInfoRow('🚌', '셔틀버스',
                            academy['셔틀버스'] == 'true' ? '운행' : '미운행'),
                        ],
                      ),
                    ),
                  ),

                  SizedBox(height: 16),

                  // 과목 정보 섹션
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '📚 과목',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              if (academy['과목_수학'] == true)
                                _buildChip('수학', Colors.red),
                              if (academy['과목_영어'] == true)
                                _buildChip('영어', Colors.blue),
                              if (academy['과목_과학'] == true)
                                _buildChip('과학', Colors.green),
                              if (academy['과목_외국어'] == true)
                                _buildChip('외국어', Colors.purple),
                              if (academy['과목_예체능'] == true)
                                _buildChip('예체능', Colors.orange),
                              if (academy['과목_컴퓨터'] == true)
                                _buildChip('컴퓨터', Colors.cyan),
                              if (academy['과목_논술'] == true)
                                _buildChip('논술', Colors.brown),
                              if (academy['과목_기타'] == true)
                                _buildChip('기타', Colors.grey),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),

                  SizedBox(height: 16),

                  // 수강료 비교 차트 섹션
                  if (_shouldShowTuitionChart(academy['수강료_평균']))
                    TuitionComparisonChart(academy: academy),

                  if (_shouldShowTuitionChart(academy['수강료_평균']))
                    SizedBox(height: 16),

                  // 대상 연령 섹션
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '👶 대상 연령',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              if (academy['대상_유아'] == true)
                                _buildChip('유아', Colors.pink),
                              if (academy['대상_초등'] == true)
                                _buildChip('초등', Colors.blue),
                              if (academy['대상_중등'] == true)
                                _buildChip('중등', Colors.green),
                              if (academy['대상_고등'] == true)
                                _buildChip('고등', Colors.orange),
                              if (academy['대상_특목고'] == true)
                                _buildChip('특목고', Colors.purple),
                              if (academy['대상_일반'] == true)
                                _buildChip('일반', Colors.grey),
                              if (academy['대상_기타'] == true)
                                _buildChip('기타', Colors.brown),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),

                  SizedBox(height: 16),

                  // 추가 정보 섹션
                  if (academy['홈페이지'] != null && academy['홈페이지'].isNotEmpty)
                    Card(
                      child: ListTile(
                        leading: Icon(Icons.language, color: Colors.blue),
                        title: Text('홈페이지'),
                        subtitle: Text(academy['홈페이지']),
                        trailing: Icon(Icons.open_in_new),
                        onTap: () {
                          html.window.open(academy['홈페이지'], '_blank');
                        },
                      ),
                    ),

                  SizedBox(height: 80), // 하단 여백
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}