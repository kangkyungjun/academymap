import 'package:flutter/material.dart';
import '../utils/constants.dart';

class CustomErrorWidget extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final IconData? icon;
  final String? retryButtonText;
  final bool showRetryButton;

  const CustomErrorWidget({
    Key? key,
    required this.message,
    this.onRetry,
    this.icon,
    this.retryButtonText,
    this.showRetryButton = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.all(AppConstants.paddingLarge),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon ?? Icons.error_outline,
            size: 64,
            color: AppConstants.errorColor,
          ),
          const SizedBox(height: AppConstants.paddingMedium),
          Text(
            message,
            style: theme.textTheme.bodyLarge?.copyWith(
              color: AppConstants.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          if (showRetryButton && onRetry != null) ..[
            const SizedBox(height: AppConstants.paddingLarge),
            ElevatedButton(
              onPressed: onRetry,
              child: Text(retryButtonText ?? AppConstants.buttonRetry),
            ),
          ],
        ],
      ),
    );
  }
}

class NetworkErrorWidget extends StatelessWidget {
  final VoidCallback? onRetry;
  final String? message;

  const NetworkErrorWidget({
    Key? key,
    this.onRetry,
    this.message,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return CustomErrorWidget(
      message: message ?? AppConstants.errorNetworkConnection,
      onRetry: onRetry,
      icon: Icons.wifi_off,
    );
  }
}

class EmptyStateWidget extends StatelessWidget {
  final String message;
  final String? actionText;
  final VoidCallback? onAction;
  final IconData? icon;

  const EmptyStateWidget({
    Key? key,
    required this.message,
    this.actionText,
    this.onAction,
    this.icon,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.all(AppConstants.paddingLarge),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon ?? Icons.inbox_outlined,
            size: 64,
            color: AppConstants.textDisabled,
          ),
          const SizedBox(height: AppConstants.paddingMedium),
          Text(
            message,
            style: theme.textTheme.bodyLarge?.copyWith(
              color: AppConstants.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          if (actionText != null && onAction != null) ..[
            const SizedBox(height: AppConstants.paddingLarge),
            OutlinedButton(
              onPressed: onAction,
              child: Text(actionText!),
            ),
          ],
        ],
      ),
    );
  }
}

class LocationPermissionWidget extends StatelessWidget {
  final VoidCallback? onRequestPermission;
  final VoidCallback? onOpenSettings;
  final bool isPermanentlyDenied;

  const LocationPermissionWidget({
    Key? key,
    this.onRequestPermission,
    this.onOpenSettings,
    this.isPermanentlyDenied = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.all(AppConstants.paddingLarge),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.location_off,
            size: 64,
            color: AppConstants.warningColor,
          ),
          const SizedBox(height: AppConstants.paddingMedium),
          Text(
            isPermanentlyDenied
                ? '위치 권한이 영구적으로 거부되었습니다.'
                : AppConstants.errorLocationPermission,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppConstants.paddingSmall),
          Text(
            isPermanentlyDenied
                ? '설정에서 위치 권한을 직접 허용해주세요.'
                : '근처 학원을 찾기 위해서는 위치 권한이 필요합니다.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: AppConstants.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppConstants.paddingLarge),
          if (isPermanentlyDenied)
            ElevatedButton(
              onPressed: onOpenSettings,
              child: const Text('설정으로 이동'),
            )
          else
            ElevatedButton(
              onPressed: onRequestPermission,
              child: const Text('권한 허용하기'),
            ),
        ],
      ),
    );
  }
}