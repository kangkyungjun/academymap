import 'package:flutter/material.dart';
import '../utils/constants.dart';

class CategoryChips extends StatelessWidget {
  final List<String> categories;
  final String selectedCategory;
  final ValueChanged<String> onCategorySelected;
  final ScrollController? scrollController;
  final EdgeInsetsGeometry? padding;
  final double spacing;

  const CategoryChips({
    Key? key,
    required this.categories,
    required this.selectedCategory,
    required this.onCategorySelected,
    this.scrollController,
    this.padding,
    this.spacing = AppConstants.paddingSmall,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      height: 40,
      padding: padding,
      child: ListView.separated(
        controller: scrollController,
        scrollDirection: Axis.horizontal,
        itemCount: categories.length,
        separatorBuilder: (context, index) => SizedBox(width: spacing),
        itemBuilder: (context, index) {
          final category = categories[index];
          final isSelected = category == selectedCategory;

          return FilterChip(
            label: Text(
              category,
              style: theme.textTheme.bodySmall?.copyWith(
                color: isSelected
                    ? theme.colorScheme.onPrimary
                    : theme.colorScheme.onSurface,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
            selected: isSelected,
            onSelected: (selected) {
              if (selected) {
                onCategorySelected(category);
              }
            },
            backgroundColor: theme.colorScheme.surface,
            selectedColor: theme.colorScheme.primary,
            checkmarkColor: theme.colorScheme.onPrimary,
            side: BorderSide(
              color: isSelected
                  ? theme.colorScheme.primary
                  : theme.colorScheme.outline.withOpacity(0.3),
              width: 1,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: VisualDensity.compact,
            padding: const EdgeInsets.symmetric(
              horizontal: AppConstants.paddingMedium,
              vertical: AppConstants.paddingSmall,
            ),
          );
        },
      ),
    );
  }
}

class CategoryFilter {
  final String key;
  final String label;
  final IconData? icon;
  final bool isSelected;

  const CategoryFilter({
    required this.key,
    required this.label,
    this.icon,
    this.isSelected = false,
  });

  CategoryFilter copyWith({
    String? key,
    String? label,
    IconData? icon,
    bool? isSelected,
  }) {
    return CategoryFilter(
      key: key ?? this.key,
      label: label ?? this.label,
      icon: icon ?? this.icon,
      isSelected: isSelected ?? this.isSelected,
    );
  }
}

class CategoryFilterChips extends StatelessWidget {
  final List<CategoryFilter> filters;
  final ValueChanged<CategoryFilter> onFilterSelected;
  final ScrollController? scrollController;
  final EdgeInsetsGeometry? padding;
  final double spacing;

  const CategoryFilterChips({
    Key? key,
    required this.filters,
    required this.onFilterSelected,
    this.scrollController,
    this.padding,
    this.spacing = AppConstants.paddingSmall,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      height: 40,
      padding: padding,
      child: ListView.separated(
        controller: scrollController,
        scrollDirection: Axis.horizontal,
        itemCount: filters.length,
        separatorBuilder: (context, index) => SizedBox(width: spacing),
        itemBuilder: (context, index) {
          final filter = filters[index];

          return FilterChip(
            avatar: filter.icon != null
                ? Icon(
                    filter.icon!,
                    size: 16,
                    color: filter.isSelected
                        ? theme.colorScheme.onPrimary
                        : theme.colorScheme.onSurface,
                  )
                : null,
            label: Text(
              filter.label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: filter.isSelected
                    ? theme.colorScheme.onPrimary
                    : theme.colorScheme.onSurface,
                fontWeight: filter.isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
            selected: filter.isSelected,
            onSelected: (selected) {
              onFilterSelected(filter.copyWith(isSelected: selected));
            },
            backgroundColor: theme.colorScheme.surface,
            selectedColor: theme.colorScheme.primary,
            checkmarkColor: theme.colorScheme.onPrimary,
            side: BorderSide(
              color: filter.isSelected
                  ? theme.colorScheme.primary
                  : theme.colorScheme.outline.withOpacity(0.3),
              width: 1,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: VisualDensity.compact,
            padding: const EdgeInsets.symmetric(
              horizontal: AppConstants.paddingMedium,
              vertical: AppConstants.paddingSmall,
            ),
          );
        },
      ),
    );
  }
}