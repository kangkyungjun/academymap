from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Bookmark, BookmarkFolder
from .bookmark_serializers import (
    BookmarkSerializer, BookmarkListSerializer, 
    BookmarkFolderSerializer, BookmarkFolderListSerializer,
    BookmarkBulkActionSerializer
)


class BookmarkPagination(PageNumberPagination):
    """즐겨찾기 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def bookmark_list_create(request):
    """즐겨찾기 목록 조회 및 생성"""
    
    if request.method == 'GET':
        # 즐겨찾기 목록 조회
        bookmarks = Bookmark.objects.filter(user=request.user).select_related('academy')
        
        # 폴더 필터링
        folder_id = request.query_params.get('folder_id')
        if folder_id:
            if folder_id == '0':  # 폴더 없음
                bookmarks = bookmarks.filter(folders__isnull=True)
            else:
                bookmarks = bookmarks.filter(folders__id=folder_id)
        
        # 우선순위 필터링
        priority = request.query_params.get('priority')
        if priority:
            bookmarks = bookmarks.filter(priority=priority)
        
        # 태그 필터링
        tags = request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                bookmarks = bookmarks.filter(tags__contains=[tag.strip()])
        
        # 정렬
        order_by = request.query_params.get('order_by', '-created_at')
        bookmarks = bookmarks.order_by(order_by)
        
        # 페이지네이션
        paginator = BookmarkPagination()
        page = paginator.paginate_queryset(bookmarks, request)
        
        if page is not None:
            serializer = BookmarkListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = BookmarkListSerializer(bookmarks, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # 즐겨찾기 생성
        serializer = BookmarkSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            bookmark = serializer.save()
            
            # 폴더에 추가
            folder_id = request.data.get('folder_id')
            if folder_id:
                try:
                    folder = BookmarkFolder.objects.get(id=folder_id, user=request.user)
                    folder.bookmarks.add(bookmark)
                except BookmarkFolder.DoesNotExist:
                    pass
            
            response_serializer = BookmarkListSerializer(bookmark)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def bookmark_detail(request, pk):
    """즐겨찾기 상세 조회, 수정, 삭제"""
    
    bookmark = get_object_or_404(Bookmark, pk=pk, user=request.user)
    
    if request.method == 'GET':
        serializer = BookmarkSerializer(bookmark)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BookmarkSerializer(
            bookmark, 
            data=request.data, 
            context={'request': request},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        bookmark.delete()
        return Response({'message': '즐겨찾기가 삭제되었습니다.'}, 
                       status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def bookmark_folder_list_create(request):
    """즐겨찾기 폴더 목록 조회 및 생성"""
    
    if request.method == 'GET':
        folders = BookmarkFolder.objects.filter(user=request.user).prefetch_related('bookmarks')
        
        # 정렬
        order_by = request.query_params.get('order_by', 'order')
        folders = folders.order_by(order_by)
        
        serializer = BookmarkFolderListSerializer(folders, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = BookmarkFolderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            folder = serializer.save()
            response_serializer = BookmarkFolderListSerializer(folder)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def bookmark_folder_detail(request, pk):
    """즐겨찾기 폴더 상세 조회, 수정, 삭제"""
    
    folder = get_object_or_404(BookmarkFolder, pk=pk, user=request.user)
    
    if request.method == 'GET':
        serializer = BookmarkFolderSerializer(folder)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BookmarkFolderSerializer(
            folder, 
            data=request.data, 
            context={'request': request},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if folder.is_default:
            return Response(
                {'error': '기본 폴더는 삭제할 수 없습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        folder.delete()
        return Response({'message': '폴더가 삭제되었습니다.'}, 
                       status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bookmark_bulk_action(request):
    """즐겨찾기 일괄 작업"""
    
    serializer = BookmarkBulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    bookmark_ids = serializer.validated_data['bookmark_ids']
    action = serializer.validated_data['action']
    
    # 사용자의 즐겨찾기만 선택
    bookmarks = Bookmark.objects.filter(
        id__in=bookmark_ids, 
        user=request.user
    )
    
    if not bookmarks.exists():
        return Response(
            {'error': '선택된 즐겨찾기를 찾을 수 없습니다.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    with transaction.atomic():
        if action == 'delete':
            count = bookmarks.count()
            bookmarks.delete()
            return Response({
                'message': f'{count}개의 즐겨찾기가 삭제되었습니다.'
            })
        
        elif action == 'move_to_folder':
            folder_id = serializer.validated_data.get('folder_id')
            try:
                folder = BookmarkFolder.objects.get(id=folder_id, user=request.user)
                
                # 기존 폴더에서 제거
                for bookmark in bookmarks:
                    bookmark.folders.clear()
                
                # 새 폴더에 추가
                folder.bookmarks.add(*bookmarks)
                
                return Response({
                    'message': f'{bookmarks.count()}개의 즐겨찾기가 {folder.name} 폴더로 이동되었습니다.'
                })
            except BookmarkFolder.DoesNotExist:
                return Response(
                    {'error': '폴더를 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif action == 'add_tags':
            tags = serializer.validated_data.get('tags', [])
            for bookmark in bookmarks:
                existing_tags = set(bookmark.tags or [])
                new_tags = existing_tags.union(set(tags))
                bookmark.tags = list(new_tags)
                bookmark.save()
            
            return Response({
                'message': f'{bookmarks.count()}개의 즐겨찾기에 태그가 추가되었습니다.'
            })
        
        elif action == 'remove_tags':
            tags = serializer.validated_data.get('tags', [])
            for bookmark in bookmarks:
                existing_tags = set(bookmark.tags or [])
                remaining_tags = existing_tags.difference(set(tags))
                bookmark.tags = list(remaining_tags)
                bookmark.save()
            
            return Response({
                'message': f'{bookmarks.count()}개의 즐겨찾기에서 태그가 제거되었습니다.'
            })
        
        elif action == 'set_priority':
            priority = serializer.validated_data.get('priority')
            bookmarks.update(priority=priority)
            
            return Response({
                'message': f'{bookmarks.count()}개의 즐겨찾기 우선순위가 변경되었습니다.'
            })
    
    return Response(
        {'error': '지원하지 않는 작업입니다.'}, 
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def bookmark_stats(request):
    """즐겨찾기 통계"""
    
    user = request.user
    
    # 전체 즐겨찾기 수
    total_bookmarks = Bookmark.objects.filter(user=user).count()
    
    # 폴더별 즐겨찾기 수
    folder_stats = []
    folders = BookmarkFolder.objects.filter(user=user).prefetch_related('bookmarks')
    
    for folder in folders:
        folder_stats.append({
            'folder_id': folder.id,
            'folder_name': folder.name,
            'bookmark_count': folder.bookmarks.count(),
            'color': folder.color,
            'icon': folder.icon
        })
    
    # 우선순위별 통계
    priority_stats = []
    for priority_value, priority_label in Bookmark._meta.get_field('priority').choices:
        count = Bookmark.objects.filter(user=user, priority=priority_value).count()
        priority_stats.append({
            'priority': priority_value,
            'label': priority_label,
            'count': count
        })
    
    # 최근 추가된 즐겨찾기
    recent_bookmarks = Bookmark.objects.filter(user=user).order_by('-created_at')[:5]
    recent_serializer = BookmarkListSerializer(recent_bookmarks, many=True)
    
    # 인기 태그
    all_bookmarks = Bookmark.objects.filter(user=user).exclude(tags__isnull=True)
    tag_counts = {}
    for bookmark in all_bookmarks:
        for tag in bookmark.tags or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return Response({
        'total_bookmarks': total_bookmarks,
        'folder_stats': folder_stats,
        'priority_stats': priority_stats,
        'recent_bookmarks': recent_serializer.data,
        'popular_tags': [{'tag': tag, 'count': count} for tag, count in popular_tags]
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_default_folder(request):
    """기본 폴더 생성"""
    
    user = request.user
    
    # 기본 폴더가 이미 있는지 확인
    if BookmarkFolder.objects.filter(user=user, is_default=True).exists():
        return Response(
            {'error': '기본 폴더가 이미 존재합니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 기본 폴더 생성
    folder = BookmarkFolder.objects.create(
        user=user,
        name='즐겨찾기',
        description='기본 즐겨찾기 폴더',
        is_default=True,
        order=0
    )
    
    serializer = BookmarkFolderListSerializer(folder)
    return Response(serializer.data, status=status.HTTP_201_CREATED)