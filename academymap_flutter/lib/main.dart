import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const AcademyMapApp());
}

class AcademyMapApp extends StatelessWidget {
  const AcademyMapApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '🏫 AcademyMap',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const AcademyMapHomePage(),
    );
  }
}

class AcademyMapHomePage extends StatefulWidget {
  const AcademyMapHomePage({super.key});

  @override
  State<AcademyMapHomePage> createState() => _AcademyMapHomePageState();
}

class _AcademyMapHomePageState extends State<AcademyMapHomePage> {
  List<dynamic> academies = [];
  bool isLoading = false;
  String selectedSubject = '전체';
  int totalCount = 0;

  final List<String> subjects = [
    '전체', '수학', '영어', '국어', '과학', '사회', '논술', '코딩'
  ];

  @override
  void initState() {
    super.initState();
    loadAcademies();
  }

  Future<void> loadAcademies() async {
    setState(() {
      isLoading = true;
    });

    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8000/api/filtered_academies'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'swLat': 37.4,  // 서울 남쪽
          'swLng': 126.8, // 서울 서쪽  
          'neLat': 37.7,  // 서울 북쪽
          'neLng': 127.2, // 서울 동쪽
          'subjects': [selectedSubject],
        }),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(utf8.decode(response.bodyBytes));
        setState(() {
          academies = data.take(50).toList(); // 처음 50개만 표시
          totalCount = data.length;
          isLoading = false;
        });
      } else {
        throw Exception('Failed to load academies');
      }
    } catch (e) {
      setState(() {
        isLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('오류: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('🏫 학원 지도'),
        elevation: 2,
      ),
      body: Column(
        children: [
          // 필터 섹션
          Container(
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(
              color: Colors.grey[50],
              border: Border(
                bottom: BorderSide(color: Colors.grey[300]!),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '📚 과목 선택',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8.0,
                  children: subjects.map((subject) {
                    return FilterChip(
                      label: Text(subject),
                      selected: selectedSubject == subject,
                      onSelected: (bool selected) {
                        if (selected) {
                          setState(() {
                            selectedSubject = subject;
                          });
                          loadAcademies();
                        }
                      },
                      selectedColor: Colors.blue[100],
                      checkmarkColor: Colors.blue[800],
                    );
                  }).toList(),
                ),
                if (totalCount > 0) ...[
                  const SizedBox(height: 8),
                  Text(
                    '📊 총 $totalCount개 학원 (상위 50개 표시)',
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 14,
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          // 학원 목록
          Expanded(
            child: isLoading
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('학원 정보를 불러오는 중...'),
                      ],
                    ),
                  )
                : academies.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.school_outlined,
                              size: 64,
                              color: Colors.grey,
                            ),
                            SizedBox(height: 16),
                            Text(
                              '학원이 없습니다',
                              style: TextStyle(
                                fontSize: 18,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: loadAcademies,
                        child: ListView.builder(
                          itemCount: academies.length,
                          itemBuilder: (context, index) {
                            final academy = academies[index];
                            return Card(
                              margin: const EdgeInsets.symmetric(
                                horizontal: 16.0,
                                vertical: 4.0,
                              ),
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: Colors.blue[100],
                                  child: const Icon(
                                    Icons.school,
                                    color: Colors.blue,
                                  ),
                                ),
                                title: Text(
                                  academy['상호명'] ?? '이름 없음',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      academy['도로명주소'] ?? '주소 없음',
                                      style: TextStyle(
                                        color: Colors.grey[600],
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Row(
                                      children: [
                                        Icon(
                                          Icons.location_on,
                                          size: 16,
                                          color: Colors.red[400],
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          '${academy['위도']?.toString().substring(0, 7) ?? 'N/A'}, ${academy['경도']?.toString().substring(0, 8) ?? 'N/A'}',
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: Colors.grey[500],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                                trailing: Icon(
                                  Icons.arrow_forward_ios,
                                  size: 16,
                                  color: Colors.grey[400],
                                ),
                                onTap: () {
                                  // 상세 정보 표시
                                  showDialog(
                                    context: context,
                                    builder: (context) => AlertDialog(
                                      title: Text(academy['상호명'] ?? '학원 정보'),
                                      content: Column(
                                        mainAxisSize: MainAxisSize.min,
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text('📍 주소: ${academy['도로명주소'] ?? 'N/A'}'),
                                          const SizedBox(height: 8),
                                          Text('🌍 좌표: ${academy['위도']}, ${academy['경도']}'),
                                          const SizedBox(height: 8),
                                          Text('📞 전화: ${academy['전화번호'] ?? 'N/A'}'),
                                        ],
                                      ),
                                      actions: [
                                        TextButton(
                                          onPressed: () => Navigator.pop(context),
                                          child: const Text('닫기'),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: loadAcademies,
        tooltip: '새로고침',
        child: const Icon(Icons.refresh),
      ),
    );
  }
}