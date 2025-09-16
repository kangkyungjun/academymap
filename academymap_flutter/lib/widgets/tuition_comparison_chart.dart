import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class TuitionComparisonChart extends StatefulWidget {
  final Map<String, dynamic> academy;

  const TuitionComparisonChart({Key? key, required this.academy}) : super(key: key);

  @override
  State<TuitionComparisonChart> createState() => _TuitionComparisonChartState();
}

class _TuitionComparisonChartState extends State<TuitionComparisonChart> {
  Map<String, dynamic>? statisticsData;
  bool isLoading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    fetchTuitionStatistics();
  }

  Future<void> fetchTuitionStatistics() async {
    try {
      final academyId = widget.academy['id'];
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8000/api/v1/academies/$academyId/tuition-statistics/'),
      );

      if (response.statusCode == 200) {
        setState(() {
          statisticsData = json.decode(utf8.decode(response.bodyBytes));
          isLoading = false;
        });
      } else {
        setState(() {
          errorMessage = '데이터를 불러오는데 실패했습니다.';
          isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        errorMessage = '네트워크 오류가 발생했습니다: $e';
        isLoading = false;
      });
    }
  }

  String formatCurrency(double? value) {
    if (value == null) return '정보 없음';
    final formatter = (value / 10000).toStringAsFixed(0);
    return '$formatter만원';
  }

  double? getTuitionValue(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    if (value is String) {
      final cleanValue = value.replaceAll(',', '').replaceAll('원', '');
      return double.tryParse(cleanValue);
    }
    return null;
  }

  List<BarChartGroupData> _generateBarGroups() {
    if (statisticsData == null) return [];

    final academy = statisticsData!['academy'];
    final statistics = statisticsData!['statistics'];

    final academyTuition = getTuitionValue(academy['tuition']);
    final dongAvg = statistics['dong']?['average']?.toDouble();
    final sigunguAvg = statistics['sigungu']?['average']?.toDouble();
    final sidoAvg = statistics['sido']?['average']?.toDouble();
    final nationalAvg = statistics['national']?['average']?.toDouble();

    List<BarChartGroupData> barGroups = [];
    int index = 0;

    // 학원 수강료
    if (academyTuition != null) {
      barGroups.add(
        BarChartGroupData(
          x: index++,
          barRods: [
            BarChartRodData(
              toY: academyTuition / 10000, // 만원 단위로 변환
              color: const Color(0xFF007BFF),
              width: 20,
              borderRadius: BorderRadius.circular(4),
            ),
          ],
        ),
      );
    }

    // 동 평균
    if (dongAvg != null) {
      barGroups.add(
        BarChartGroupData(
          x: index++,
          barRods: [
            BarChartRodData(
              toY: dongAvg / 10000,
              color: const Color(0xFFCCCCCC),
              width: 20,
              borderRadius: BorderRadius.circular(4),
            ),
          ],
        ),
      );
    }

    // 구 평균
    if (sigunguAvg != null) {
      barGroups.add(
        BarChartGroupData(
          x: index++,
          barRods: [
            BarChartRodData(
              toY: sigunguAvg / 10000,
              color: const Color(0xFF999999),
              width: 20,
              borderRadius: BorderRadius.circular(4),
            ),
          ],
        ),
      );
    }

    // 시 평균
    if (sidoAvg != null) {
      barGroups.add(
        BarChartGroupData(
          x: index++,
          barRods: [
            BarChartRodData(
              toY: sidoAvg / 10000,
              color: const Color(0xFF666666),
              width: 20,
              borderRadius: BorderRadius.circular(4),
            ),
          ],
        ),
      );
    }

    // 전국 평균
    if (nationalAvg != null) {
      barGroups.add(
        BarChartGroupData(
          x: index++,
          barRods: [
            BarChartRodData(
              toY: nationalAvg / 10000,
              color: const Color(0xFF333333),
              width: 20,
              borderRadius: BorderRadius.circular(4),
            ),
          ],
        ),
      );
    }

    return barGroups;
  }

  List<String> _getBottomTitles() {
    if (statisticsData == null) return [];

    final statistics = statisticsData!['statistics'];
    List<String> titles = [];

    if (getTuitionValue(statisticsData!['academy']['tuition']) != null) {
      titles.add('학원');
    }
    if (statistics['dong'] != null) {
      titles.add(statistics['dong']['name'] ?? '동');
    }
    if (statistics['sigungu'] != null) {
      titles.add(statistics['sigungu']['name'] ?? '구');
    }
    if (statistics['sido'] != null) {
      titles.add(statistics['sido']['name'] ?? '시');
    }
    if (statistics['national'] != null) {
      titles.add('전국');
    }

    return titles;
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Card(
        child: Container(
          height: 350,
          padding: const EdgeInsets.all(16.0),
          child: const Center(
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    if (errorMessage != null) {
      return Card(
        child: Container(
          height: 350,
          padding: const EdgeInsets.all(16.0),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 48, color: Colors.grey),
                SizedBox(height: 16),
                Text(errorMessage!, style: TextStyle(color: Colors.grey[600])),
                SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    setState(() {
                      isLoading = true;
                      errorMessage = null;
                    });
                    fetchTuitionStatistics();
                  },
                  child: Text('다시 시도'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final barGroups = _generateBarGroups();
    final bottomTitles = _getBottomTitles();

    if (barGroups.isEmpty) {
      return Card(
        child: Container(
          height: 350,
          padding: const EdgeInsets.all(16.0),
          child: Center(
            child: Text(
              '수강료 정보가 없습니다',
              style: TextStyle(color: Colors.grey[600], fontSize: 16),
            ),
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '💰 수강료 비교',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(width: 8),
                Tooltip(
                  message: '지역별 평균 수강료와 비교합니다',
                  child: Icon(Icons.info_outline, size: 18, color: Colors.grey),
                ),
              ],
            ),
            SizedBox(height: 20),

            // 범례
            Wrap(
              spacing: 16,
              children: [
                _buildLegendItem('학원', const Color(0xFF007BFF)),
                _buildLegendItem('동 평균', const Color(0xFFCCCCCC)),
                _buildLegendItem('구 평균', const Color(0xFF999999)),
                _buildLegendItem('시 평균', const Color(0xFF666666)),
                _buildLegendItem('전국 평균', const Color(0xFF333333)),
              ],
            ),
            SizedBox(height: 20),

            // 차트
            Container(
              height: 250,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  maxY: barGroups.map((g) => g.barRods[0].toY).reduce((a, b) => a > b ? a : b) * 1.2,
                  barGroups: barGroups,
                  titlesData: FlTitlesData(
                    show: true,
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          if (value.toInt() < bottomTitles.length) {
                            return Padding(
                              padding: const EdgeInsets.only(top: 8.0),
                              child: Text(
                                bottomTitles[value.toInt()],
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: value == 0 ? FontWeight.bold : FontWeight.normal,
                                ),
                              ),
                            );
                          }
                          return Text('');
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            '${value.toInt()}만원',
                            style: TextStyle(fontSize: 10),
                          );
                        },
                        interval: 10,
                      ),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: 10,
                    getDrawingHorizontalLine: (value) {
                      return FlLine(
                        color: Colors.grey[300]!,
                        strokeWidth: 1,
                      );
                    },
                  ),
                  borderData: FlBorderData(
                    show: true,
                    border: Border(
                      left: BorderSide(color: Colors.grey[400]!),
                      bottom: BorderSide(color: Colors.grey[400]!),
                    ),
                  ),
                  barTouchData: BarTouchData(
                    enabled: true,
                    touchTooltipData: BarTouchTooltipData(
                      getTooltipItem: (group, groupIndex, rod, rodIndex) {
                        final title = groupIndex < bottomTitles.length
                          ? bottomTitles[groupIndex]
                          : '';
                        return BarTooltipItem(
                          '$title\n${rod.toY.toStringAsFixed(0)}만원',
                          TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                        );
                      },
                    ),
                  ),
                ),
              ),
            ),

            // 데이터 개수 표시
            if (statisticsData != null) ...[
              SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  if (statisticsData!['statistics']['dong'] != null)
                    _buildCountInfo(
                      '${statisticsData!['statistics']['dong']['name']}',
                      '${statisticsData!['statistics']['dong']['count']}개 학원',
                    ),
                  if (statisticsData!['statistics']['sigungu'] != null)
                    _buildCountInfo(
                      '${statisticsData!['statistics']['sigungu']['name']}',
                      '${statisticsData!['statistics']['sigungu']['count']}개 학원',
                    ),
                  if (statisticsData!['statistics']['national'] != null)
                    _buildCountInfo(
                      '전국',
                      '${statisticsData!['statistics']['national']['count']}개 학원',
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 12)),
      ],
    );
  }

  Widget _buildCountInfo(String title, String count) {
    return Column(
      children: [
        Text(
          title,
          style: TextStyle(fontSize: 11, color: Colors.grey[600]),
        ),
        Text(
          count,
          style: TextStyle(fontSize: 10, color: Colors.grey[500]),
        ),
      ],
    );
  }
}