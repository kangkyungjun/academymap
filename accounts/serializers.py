from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserPreference


class UserRegistrationSerializer(serializers.ModelSerializer):
    """사용자 회원가입 시리얼라이저"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'nickname', 'phone', 'birth_date',
            'password', 'password_confirm', 'preferred_areas', 
            'interested_subjects', 'child_ages'
        ]
        
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return attrs
        
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # 기본 사용자 설정 생성
        UserPreference.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """사용자 로그인 시리얼라이저"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
            if not user.is_active:
                raise serializers.ValidationError("비활성화된 계정입니다.")
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("이메일과 비밀번호를 입력해주세요.")


class UserProfileSerializer(serializers.ModelSerializer):
    """사용자 프로필 시리얼라이저"""
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'nickname', 'phone', 'birth_date',
            'preferred_areas', 'interested_subjects', 'child_ages', 
            'date_joined', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'created_at', 'updated_at']


class UserPreferenceSerializer(serializers.ModelSerializer):
    """사용자 설정 시리얼라이저"""
    class Meta:
        model = UserPreference
        fields = [
            'theme', 'default_location', 'email_notifications', 
            'push_notifications', 'new_academy_alerts'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """비밀번호 변경 시리얼라이저"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("기존 비밀번호가 올바르지 않습니다.")
        return value
        
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        return attrs
        
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user