from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404
from .models import User, UserPreference
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserPreferenceSerializer, PasswordChangeSerializer
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """사용자 회원가입"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': '회원가입이 완료되었습니다.',
            'token': token.key,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'nickname': user.nickname
            }
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': '회원가입에 실패했습니다.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_login(request):
    """사용자 로그인"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': '로그인에 성공했습니다.',
            'token': token.key,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'nickname': user.nickname
            }
        }, status=status.HTTP_200_OK)
    return Response({
        'message': '로그인에 실패했습니다.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def user_logout(request):
    """사용자 로그아웃"""
    try:
        # 토큰 삭제
        request.user.auth_token.delete()
        return Response({
            'message': '로그아웃 되었습니다.'
        }, status=status.HTTP_200_OK)
    except:
        return Response({
            'message': '로그아웃에 실패했습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def profile(request):
    """사용자 프로필 조회/수정"""
    user = request.user
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(user)
        return Response({
            'user': serializer.data
        }, status=status.HTTP_200_OK)
        
    elif request.method in ['PUT', 'PATCH']:
        serializer = UserProfileSerializer(user, data=request.data, partial=request.method == 'PATCH')
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '프로필이 업데이트되었습니다.',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            'message': '프로필 업데이트에 실패했습니다.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def preferences(request):
    """사용자 설정 조회/수정"""
    preference, created = UserPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        serializer = UserPreferenceSerializer(preference)
        return Response({
            'preferences': serializer.data
        }, status=status.HTTP_200_OK)
        
    elif request.method in ['PUT', 'PATCH']:
        serializer = UserPreferenceSerializer(preference, data=request.data, partial=request.method == 'PATCH')
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '설정이 업데이트되었습니다.',
                'preferences': serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            'message': '설정 업데이트에 실패했습니다.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """비밀번호 변경"""
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': '비밀번호가 변경되었습니다.'
        }, status=status.HTTP_200_OK)
    return Response({
        'message': '비밀번호 변경에 실패했습니다.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_account(request):
    """계정 삭제"""
    user = request.user
    user.delete()
    return Response({
        'message': '계정이 삭제되었습니다.'
    }, status=status.HTTP_200_OK)
