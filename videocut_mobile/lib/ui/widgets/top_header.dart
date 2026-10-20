import 'package:flutter/material.dart';
import '../../editor_state.dart';
import 'export_modal.dart';

class TopHeader extends StatelessWidget {
  final EditorState state;
  final String selectedResolution;
  final ValueChanged<String> onResolutionChanged;

  const TopHeader({
    super.key,
    required this.state,
    required this.selectedResolution,
    required this.onResolutionChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      color: const Color(0xFF161616),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 20, color: Colors.white),
            tooltip: 'Home',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Proyek VideoCut tersimpan otomatis.'),
                  duration: Duration(seconds: 1),
                ),
              );
            },
          ),
          const SizedBox(width: 4),
          const Expanded(
            child: Text(
              'VideoCut Mobile',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 16,
                letterSpacing: 0.5,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          // Resolution selector chip
          Container(
            height: 32,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: const Color(0xFF262626),
              borderRadius: BorderRadius.circular(16),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: selectedResolution,
                dropdownColor: const Color(0xFF262626),
                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                icon: const Icon(Icons.arrow_drop_down, color: Colors.white70, size: 18),
                items: const [
                  DropdownMenuItem(value: '720P', child: Text('720P')),
                  DropdownMenuItem(value: '1080P', child: Text('1080P')),
                  DropdownMenuItem(value: '4K', child: Text('4K 60F')),
                ],
                onChanged: (val) {
                  if (val != null) onResolutionChanged(val);
                },
              ),
            ),
          ),
          const SizedBox(width: 8),
          // Export action button
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00E5FF),
              foregroundColor: Colors.black,
              elevation: 0,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            ),
            icon: const Icon(Icons.file_upload_outlined, size: 18),
            label: const Text(
              'Export',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
            onPressed: () {
              showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                builder: (ctx) => ExportModal(state: state, resolution: selectedResolution),
              );
            },
          ),
        ],
      ),
    );
  }
}
