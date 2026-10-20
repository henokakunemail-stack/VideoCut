import 'dart:async';
import 'package:flutter/material.dart';
import '../../editor_state.dart';

class ExportModal extends StatefulWidget {
  final EditorState state;
  final String resolution;

  const ExportModal({super.key, required this.state, required this.resolution});

  @override
  State<ExportModal> createState() => _ExportModalState();
}

class _ExportModalState extends State<ExportModal> {
  late String _res;
  int _fps = 30;
  final String _codec = 'H.264 (MP4)';
  bool _isExporting = false;
  double _progress = 0.0;
  bool _isCompleted = false;
  Timer? _exportTimer;

  @override
  void initState() {
    super.initState();
    _res = widget.resolution;
  }

  @override
  void dispose() {
    _exportTimer?.cancel();
    super.dispose();
  }

  double _getEstimatedSizeMb() {
    final durationSec = widget.state.totalDurationMs / 1000.0;
    double bitrateMbps = 8.0;
    if (_res == '720P') bitrateMbps = 5.0;
    if (_res == '1080P') bitrateMbps = 10.0;
    if (_res == '4K') bitrateMbps = 25.0;
    if (_fps == 60) bitrateMbps *= 1.4;
    return (bitrateMbps * durationSec) / 8.0;
  }

  void _startExport() {
    setState(() {
      _isExporting = true;
      _progress = 0.0;
      _isCompleted = false;
    });

    _exportTimer?.cancel();
    _exportTimer = Timer.periodic(const Duration(milliseconds: 50), (timer) {
      setState(() {
        _progress += 0.025;
        if (_progress >= 1.0) {
          _progress = 1.0;
          _isExporting = false;
          _isCompleted = true;
          timer.cancel();
        }
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        color: Color(0xFF1E1E1E),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header bar
            Row(
              children: [
                const Text(
                  'Pengaturan Ekspor Video',
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close_rounded, color: Colors.white60),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const Divider(color: Color(0xFF2E2E2E)),
            const SizedBox(height: 8),

            if (!_isCompleted && !_isExporting) ...[
              // Resolution Selector
              const Text('Resolusi', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              Row(
                children: ['720P', '1080P', '4K'].map((r) {
                  final isSel = _res == r;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(r, style: TextStyle(color: isSel ? Colors.black : Colors.white, fontWeight: FontWeight.bold)),
                      selected: isSel,
                      selectedColor: const Color(0xFF00E5FF),
                      backgroundColor: const Color(0xFF2E2E2E),
                      onSelected: (val) {
                        if (val) setState(() => _res = r);
                      },
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: 12),

              // Frame Rate Selector
              const Text('Frame Rate (FPS)', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              Row(
                children: [24, 30, 60].map((fps) {
                  final isSel = _fps == fps;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text('${fps}fps', style: TextStyle(color: isSel ? Colors.black : Colors.white, fontWeight: FontWeight.bold)),
                      selected: isSel,
                      selectedColor: const Color(0xFF00E5FF),
                      backgroundColor: const Color(0xFF2E2E2E),
                      onSelected: (val) {
                        if (val) setState(() => _fps = fps);
                      },
                    ),
                  );
                }).toList(),
              ),

              const SizedBox(height: 12),

              // Codec Info & Estimated Size
              Row(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Format Codec', style: TextStyle(color: Colors.white70, fontSize: 12)),
                      Text(_codec, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const Spacer(),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text('Estimasi Ukuran', style: TextStyle(color: Colors.white70, fontSize: 12)),
                      Text(
                        '~${_getEstimatedSizeMb().toStringAsFixed(1)} MB',
                        style: const TextStyle(color: Color(0xFF00E5FF), fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ],
              ),

              const SizedBox(height: 20),

              // Start Export Button
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00E5FF),
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                  ),
                  icon: const Icon(Icons.movie_creation_outlined),
                  label: const Text('Export Video Sekarang (Tanpa Watermark)', style: TextStyle(fontWeight: FontWeight.bold)),
                  onPressed: _startExport,
                ),
              ),
            ] else if (_isExporting) ...[
              // Exporting progress indicator
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24),
                  child: Column(
                    children: [
                      Text(
                        '${(_progress * 100).toInt()}%',
                        style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 36, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: LinearProgressIndicator(
                          value: _progress,
                          minHeight: 8,
                          backgroundColor: Colors.white12,
                          valueColor: const AlwaysStoppedAnimation(Color(0xFF00E5FF)),
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Merender frame, audio fx, dan filter color grading...',
                        style: TextStyle(color: Colors.white60, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            ] else ...[
              // Export completed screen
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Column(
                    children: [
                      const Icon(Icons.check_circle_rounded, color: Color(0xFF00E5FF), size: 56),
                      const SizedBox(height: 12),
                      const Text(
                        'Video Berhasil Diekspor!',
                        style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Tersimpan di: DCIM/VideoCut/VideoCut_1080p.mp4',
                        style: TextStyle(color: Colors.white60, fontSize: 12),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        height: 44,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF00E5FF),
                            foregroundColor: Colors.black,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                          ),
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Selesai & Kembali ke Editor', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
