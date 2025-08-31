import 'package:flutter/material.dart';
import '../utils/constants.dart';

class SearchBarWidget extends StatefulWidget {
  final String? hintText;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onTap;
  final bool readOnly;
  final TextEditingController? controller;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final bool autofocus;

  const SearchBarWidget({
    Key? key,
    this.hintText,
    this.onChanged,
    this.onTap,
    this.readOnly = false,
    this.controller,
    this.prefixIcon,
    this.suffixIcon,
    this.autofocus = false,
  }) : super(key: key);

  @override
  State<SearchBarWidget> createState() => _SearchBarWidgetState();
}

class _SearchBarWidgetState extends State<SearchBarWidget> {
  late TextEditingController _controller;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? TextEditingController();
    _hasText = _controller.text.isNotEmpty;
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    if (widget.controller == null) {
      _controller.dispose();
    } else {
      _controller.removeListener(_onTextChanged);
    }
    super.dispose();
  }

  void _onTextChanged() {
    final hasText = _controller.text.isNotEmpty;
    if (_hasText != hasText) {
      setState(() {
        _hasText = hasText;
      });
    }
    widget.onChanged?.call(_controller.text);
  }

  void _clearText() {
    _controller.clear();
    widget.onChanged?.call('');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        border: Border.all(
          color: theme.colorScheme.outline.withOpacity(0.3),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: TextField(
        controller: _controller,
        readOnly: widget.readOnly,
        onTap: widget.onTap,
        autofocus: widget.autofocus,
        style: theme.textTheme.bodyMedium,
        decoration: InputDecoration(
          hintText: widget.hintText ?? '학원을 검색해보세요',
          hintStyle: theme.textTheme.bodyMedium?.copyWith(
            color: AppConstants.textDisabled,
          ),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: AppConstants.paddingMedium,
            vertical: AppConstants.paddingMedium,
          ),
          prefixIcon: widget.prefixIcon ??
              Icon(
                Icons.search,
                color: AppConstants.textSecondary,
                size: 20,
              ),
          suffixIcon: widget.suffixIcon ??
              (_hasText && !widget.readOnly
                  ? IconButton(
                      icon: Icon(
                        Icons.clear,
                        color: AppConstants.textSecondary,
                        size: 20,
                      ),
                      onPressed: _clearText,
                      constraints: const BoxConstraints(
                        minWidth: 32,
                        minHeight: 32,
                      ),
                    )
                  : null),
        ),
      ),
    );
  }
}