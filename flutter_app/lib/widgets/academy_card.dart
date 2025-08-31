import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/academy.dart';
import '../utils/constants.dart';

class AcademyCard extends StatelessWidget {
  final Academy academy;
  final VoidCallback? onTap;
  final VoidCallback? onFavoritePressed;
  final bool isFavorite;
  final bool showRanking;
  final int? ranking;
  final bool isCompact;
  
  const AcademyCard({
    Key? key,
    required this.academy,
    this.onTap,
    this.onFavoritePressed,
    this.isFavorite = false,
    this.showRanking = false,
    this.ranking,
    this.isCompact = false,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: AppConstants.elevatedShadow[0].blurRadius,
      shadowColor: AppConstants.elevatedShadow[0].color,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        child: Container(
          height: isCompact ? AppConstants.compactListItemHeight : AppConstants.listItemHeight,
          padding: const EdgeInsets.all(AppConstants.paddingMedium),
          child: isCompact ? _buildCompactLayout(theme) : _buildFullLayout(theme),
        ),
      ),
    );
  }
  
  Widget _buildFullLayout(ThemeData theme) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showRanking && ranking != null) ...[
          _buildRankingBadge(),
          const SizedBox(width: AppConstants.paddingSmall),
        ],
        _buildImage(),
        const SizedBox(width: AppConstants.paddingMedium),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(theme),
              const SizedBox(height: AppConstants.paddingSmall),
              _buildAddress(theme),
              const SizedBox(height: AppConstants.paddingSmall),
              _buildSubjects(theme),
              const Spacer(),
              _buildFooter(theme),
            ],
          ),
        ),
        _buildFavoriteButton(),
      ],
    );
  }
  
  Widget _buildCompactLayout(ThemeData theme) {
    return Row(
      children: [
        if (showRanking && ranking != null) ...[
          _buildRankingBadge(),
          const SizedBox(width: AppConstants.paddingSmall),
        ],
        Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            color: Colors.grey[200],
          ),
          child: _buildImageContent(60),
        ),
        const SizedBox(width: AppConstants.paddingMedium),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                academy.name,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 2),
              Text(
                academy.fullAddress,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: AppConstants.textSecondary,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 2),
              Row(
                children: [
                  if (academy.rating != null) ...[
                    Icon(
                      Icons.star,
                      size: 14,
                      color: Colors.amber,
                    ),
                    const SizedBox(width: 2),
                    Text(
                      academy.rating!.toStringAsFixed(1),
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                  if (academy.feeRange != null) ...[
                    const SizedBox(width: AppConstants.paddingSmall),
                    Text(
                      academy.feeRange!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: AppConstants.primaryColor,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
        _buildFavoriteButton(),
      ],
    );
  }
  
  Widget _buildRankingBadge() {
    return Container(
      width: 24,
      height: 24,
      decoration: BoxDecoration(
        color: ranking! <= 3 ? AppConstants.primaryColor : AppConstants.textSecondary,
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Text(
          ranking.toString(),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
  
  Widget _buildImage() {
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        color: Colors.grey[200],
      ),
      child: _buildImageContent(80),
    );
  }
  
  Widget _buildImageContent(double size) {
    if (academy.images?.isNotEmpty ?? false) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        child: CachedNetworkImage(
          imageUrl: academy.images!.first,
          width: size,
          height: size,
          fit: BoxFit.cover,
          placeholder: (context, url) => Container(
            color: Colors.grey[200],
            child: const Center(
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
          errorWidget: (context, url, error) => Container(
            color: Colors.grey[200],
            child: const Icon(
              Icons.school,
              color: AppConstants.textDisabled,
            ),
          ),
        ),
      );
    }
    
    return const Center(
      child: Icon(
        Icons.school,
        color: AppConstants.textDisabled,
        size: 32,
      ),
    );
  }
  
  Widget _buildHeader(ThemeData theme) {
    return Row(
      children: [
        Expanded(
          child: Text(
            academy.name,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (academy.rating != null) ...[
          Icon(
            Icons.star,
            size: 16,
            color: Colors.amber,
          ),
          const SizedBox(width: 2),
          Text(
            academy.rating!.toStringAsFixed(1),
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }
  
  Widget _buildAddress(ThemeData theme) {
    return Row(
      children: [
        Icon(
          Icons.location_on_outlined,
          size: 14,
          color: AppConstants.textSecondary,
        ),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            academy.fullAddress,
            style: theme.textTheme.bodySmall?.copyWith(
              color: AppConstants.textSecondary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
  
  Widget _buildSubjects(ThemeData theme) {
    final subjects = academy.subjects.take(3).toList();
    
    if (subjects.isEmpty) return const SizedBox.shrink();
    
    return Wrap(
      spacing: AppConstants.paddingSmall,
      children: subjects.map((subject) {
        return Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 6,
            vertical: 2,
          ),
          decoration: BoxDecoration(
            color: AppConstants.primaryColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            subject,
            style: theme.textTheme.bodySmall?.copyWith(
              color: AppConstants.primaryColor,
              fontSize: 10,
            ),
          ),
        );
      }).toList(),
    );
  }
  
  Widget _buildFooter(ThemeData theme) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        if (academy.feeRange != null)
          Text(
            academy.feeRange!,
            style: theme.textTheme.bodySmall?.copyWith(
              color: AppConstants.primaryColor,
              fontWeight: FontWeight.w500,
            ),
          )
        else
          const SizedBox.shrink(),
        _buildFeatures(theme),
      ],
    );
  }
  
  Widget _buildFeatures(ThemeData theme) {
    final features = <Widget>[];
    
    if (academy.hasShuttle == true) {
      features.add(
        Icon(
          Icons.directions_bus,
          size: 14,
          color: AppConstants.textSecondary,
        ),
      );
    }
    
    if (academy.hasParking == true) {
      features.add(
        Icon(
          Icons.local_parking,
          size: 14,
          color: AppConstants.textSecondary,
        ),
      );
    }
    
    if (academy.hasOnlineClass == true) {
      features.add(
        Icon(
          Icons.laptop,
          size: 14,
          color: AppConstants.textSecondary,
        ),
      );
    }
    
    if (features.isEmpty) return const SizedBox.shrink();
    
    return Row(
      children: features
          .expand((widget) => [widget, const SizedBox(width: 4)])
          .take(features.length * 2 - 1)
          .toList(),
    );
  }
  
  Widget _buildFavoriteButton() {
    return IconButton(
      icon: Icon(
        isFavorite ? Icons.favorite : Icons.favorite_border,
        color: isFavorite ? Colors.red : AppConstants.textSecondary,
        size: 20,
      ),
      onPressed: onFavoritePressed,
      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
      padding: EdgeInsets.zero,
    );
  }
}