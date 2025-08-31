import 'package:json_annotation/json_annotation.dart';
import 'package:hive/hive.dart';

part 'academy.g.dart';

@HiveType(typeId: 0)
@JsonSerializable()
class Academy {
  @HiveField(0)
  final int id;
  
  @HiveField(1)
  @JsonKey(name: '상호명')
  final String name;
  
  @HiveField(2)
  @JsonKey(name: '도로명주소')
  final String? roadAddress;
  
  @HiveField(3)
  @JsonKey(name: '지번주소')
  final String? lotAddress;
  
  @HiveField(4)
  @JsonKey(name: '시도명')
  final String? province;
  
  @HiveField(5)
  @JsonKey(name: '시군구명')
  final String? city;
  
  @HiveField(6)
  @JsonKey(name: '읍면동명')
  final String? district;
  
  @HiveField(7)
  @JsonKey(name: '위도')
  final double? latitude;
  
  @HiveField(8)
  @JsonKey(name: '경도')
  final double? longitude;
  
  @HiveField(9)
  @JsonKey(name: '전화번호')
  final String? phone;
  
  @HiveField(10)
  @JsonKey(name: '과목_수학')
  final bool subjectMath;
  
  @HiveField(11)
  @JsonKey(name: '과목_영어')
  final bool subjectEnglish;
  
  @HiveField(12)
  @JsonKey(name: '과목_과학')
  final bool subjectScience;
  
  @HiveField(13)
  @JsonKey(name: '과목_외국어')
  final bool subjectLanguage;
  
  @HiveField(14)
  @JsonKey(name: '과목_논술')
  final bool subjectEssay;
  
  @HiveField(15)
  @JsonKey(name: '과목_예체능')
  final bool subjectArts;
  
  @HiveField(16)
  @JsonKey(name: '과목_컴퓨터')
  final bool subjectComputer;
  
  @HiveField(17)
  @JsonKey(name: '과목_기타')
  final bool subjectOther;
  
  @HiveField(18)
  @JsonKey(name: '대상_초등학생')
  final bool targetElementary;
  
  @HiveField(19)
  @JsonKey(name: '대상_중학생')
  final bool targetMiddle;
  
  @HiveField(20)
  @JsonKey(name: '대상_고등학생')
  final bool targetHigh;
  
  @HiveField(21)
  @JsonKey(name: '대상_성인')
  final bool targetAdult;
  
  @HiveField(22)
  @JsonKey(name: '평점')
  final double? rating;
  
  @HiveField(23)
  @JsonKey(name: '리뷰수')
  final int? reviewCount;
  
  @HiveField(24)
  @JsonKey(name: '수강료_최소')
  final int? feeMin;
  
  @HiveField(25)
  @JsonKey(name: '수강료_최대')
  final int? feeMax;
  
  @HiveField(26)
  @JsonKey(name: '셔틀버스')
  final bool? hasShuttle;
  
  @HiveField(27)
  @JsonKey(name: '주차장')
  final bool? hasParking;
  
  @HiveField(28)
  @JsonKey(name: '온라인수업')
  final bool? hasOnlineClass;
  
  @HiveField(29)
  final String? description;
  
  @HiveField(30)
  final List<String>? images;
  
  @HiveField(31)
  final DateTime? createdAt;
  
  @HiveField(32)
  final DateTime? updatedAt;
  
  Academy({
    required this.id,
    required this.name,
    this.roadAddress,
    this.lotAddress,
    this.province,
    this.city,
    this.district,
    this.latitude,
    this.longitude,
    this.phone,
    this.subjectMath = false,
    this.subjectEnglish = false,
    this.subjectScience = false,
    this.subjectLanguage = false,
    this.subjectEssay = false,
    this.subjectArts = false,
    this.subjectComputer = false,
    this.subjectOther = false,
    this.targetElementary = false,
    this.targetMiddle = false,
    this.targetHigh = false,
    this.targetAdult = false,
    this.rating,
    this.reviewCount,
    this.feeMin,
    this.feeMax,
    this.hasShuttle,
    this.hasParking,
    this.hasOnlineClass,
    this.description,
    this.images,
    this.createdAt,
    this.updatedAt,
  });
  
  factory Academy.fromJson(Map<String, dynamic> json) => _$AcademyFromJson(json);
  
  Map<String, dynamic> toJson() => _$AcademyToJson(this);
  
  String get fullAddress {
    final parts = [roadAddress ?? lotAddress, city, district]
        .where((part) => part != null && part.isNotEmpty)
        .toList();
    return parts.join(' ');
  }
  
  List<String> get subjects {
    final List<String> result = [];
    if (subjectMath) result.add('수학');
    if (subjectEnglish) result.add('영어');
    if (subjectScience) result.add('과학');
    if (subjectLanguage) result.add('외국어');
    if (subjectEssay) result.add('논술');
    if (subjectArts) result.add('예체능');
    if (subjectComputer) result.add('컴퓨터');
    if (subjectOther) result.add('기타');
    return result;
  }
  
  List<String> get targets {
    final List<String> result = [];
    if (targetElementary) result.add('초등학생');
    if (targetMiddle) result.add('중학생');
    if (targetHigh) result.add('고등학생');
    if (targetAdult) result.add('성인');
    return result;
  }
  
  String? get feeRange {
    if (feeMin == null || feeMax == null) return null;
    if (feeMin == feeMax) return '${feeMin!.toStringAsFixed(0)}만원';
    return '${feeMin!.toStringAsFixed(0)}~${feeMax!.toStringAsFixed(0)}만원';
  }
  
  double? get distance {
    return null;
  }
  
  Academy copyWith({
    int? id,
    String? name,
    String? roadAddress,
    String? lotAddress,
    String? province,
    String? city,
    String? district,
    double? latitude,
    double? longitude,
    String? phone,
    bool? subjectMath,
    bool? subjectEnglish,
    bool? subjectScience,
    bool? subjectLanguage,
    bool? subjectEssay,
    bool? subjectArts,
    bool? subjectComputer,
    bool? subjectOther,
    bool? targetElementary,
    bool? targetMiddle,
    bool? targetHigh,
    bool? targetAdult,
    double? rating,
    int? reviewCount,
    int? feeMin,
    int? feeMax,
    bool? hasShuttle,
    bool? hasParking,
    bool? hasOnlineClass,
    String? description,
    List<String>? images,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Academy(
      id: id ?? this.id,
      name: name ?? this.name,
      roadAddress: roadAddress ?? this.roadAddress,
      lotAddress: lotAddress ?? this.lotAddress,
      province: province ?? this.province,
      city: city ?? this.city,
      district: district ?? this.district,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      phone: phone ?? this.phone,
      subjectMath: subjectMath ?? this.subjectMath,
      subjectEnglish: subjectEnglish ?? this.subjectEnglish,
      subjectScience: subjectScience ?? this.subjectScience,
      subjectLanguage: subjectLanguage ?? this.subjectLanguage,
      subjectEssay: subjectEssay ?? this.subjectEssay,
      subjectArts: subjectArts ?? this.subjectArts,
      subjectComputer: subjectComputer ?? this.subjectComputer,
      subjectOther: subjectOther ?? this.subjectOther,
      targetElementary: targetElementary ?? this.targetElementary,
      targetMiddle: targetMiddle ?? this.targetMiddle,
      targetHigh: targetHigh ?? this.targetHigh,
      targetAdult: targetAdult ?? this.targetAdult,
      rating: rating ?? this.rating,
      reviewCount: reviewCount ?? this.reviewCount,
      feeMin: feeMin ?? this.feeMin,
      feeMax: feeMax ?? this.feeMax,
      hasShuttle: hasShuttle ?? this.hasShuttle,
      hasParking: hasParking ?? this.hasParking,
      hasOnlineClass: hasOnlineClass ?? this.hasOnlineClass,
      description: description ?? this.description,
      images: images ?? this.images,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}