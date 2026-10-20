import 'package:flutter/material.dart';
import '../../editor_state.dart';

class PreviewCanvas extends StatelessWidget {
  final EditorState state;

  const PreviewCanvas({super.key, required this.state});

  double _getAspectRatio(AspectRatioMode mode) {
    switch (mode) {
      case AspectRatioMode.ratio9_16:
        return 9 / 16;
      case AspectRatioMode.ratio16_9:
        return 16 / 9;
      case AspectRatioMode.ratio1_1:
        return 1.0;
      case AspectRatioMode.ratio4_5:
        return 4 / 5;
    }
  }

  String _getRatioLabel(AspectRatioMode mode) {
    switch (mode) {
      case AspectRatioMode.ratio9_16:
        return '9:16 (TikTok)';
      case AspectRatioMode.ratio16_9:
        return '16:9 (YouTube)';
      case AspectRatioMode.ratio1_1:
        return '1:1 (Square)';
      case AspectRatioMode.ratio4_5:
        return '4:5 (Portrait)';
    }
  }

  @override
  Widget build(BuildContext context) {
    final ratio = _getAspectRatio(state.aspectRatio);

    // Active video clip at current timestamp
    final activeClip = state.videoClips.cast<ClipItem?>().firstWhere(
          (c) => c != null && c.startMs <= state.currentTimeMs && (c.startMs + c.durationMs) > state.currentTimeMs,
          orElse: () => state.videoClips.isNotEmpty ? state.videoClips.first : null,
        );

    // Active text subtitle
    final activeText = state.textClips.cast<ClipItem?>().firstWhere(
          (t) => t != null && t.startMs <= state.currentTimeMs && (t.startMs + t.durationMs) > state.currentTimeMs,
          orElse: () => null,
        );

    // Color filter matrix
    // ponytail: ColorMatrix handles contrast and brightness in 1 pass. Upgrade to fragment shader for 3D LUT.
    final c = state.contrast;
    final b = state.brightness * 255;
    final colorMatrix = <double>[
      c, 0, 0, 0, b,
      0, c, 0, 0, b,
      0, 0, c, 0, b,
      0, 0, 0, 1, 0,
    ];

    return Container(
      color: Colors.black,
      alignment: Alignment.center,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Dynamic Aspect Ratio Viewport
          AspectRatio(
            aspectRatio: ratio,
            child: ColorFiltered(
              colorFilter: ColorFilter.matrix(colorMatrix),
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      activeClip?.color ?? const Color(0xFF1E1E1E),
                      Colors.black87,
                    ],
                  ),
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Canvas grid / watermark-free watermark indicator
                    Positioned(
                      top: 12,
                      left: 12,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          _getRatioLabel(state.aspectRatio),
                          style: const TextStyle(color: Colors.white70, fontSize: 10),
                        ),
                      ),
                    ),

                    // Scene Simulation Content
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.videocam_rounded,
                          size: 48,
                          color: Colors.white.withValues(alpha: 0.8),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          activeClip?.title ?? 'No Clip',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            shadows: [Shadow(color: Colors.black, blurRadius: 4)],
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          state.formatTime(state.currentTimeMs),
                          style: const TextStyle(
                            color: Color(0xFF00E5FF),
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),

                    // Active Subtitle / Text overlay
                    if (activeText != null)
                      Positioned(
                        bottom: 30,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.65),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: const Color(0xFF00E5FF).withValues(alpha: 0.6), width: 1),
                          ),
                          child: Text(
                            activeText.title,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),

                    // Vignette Overlay
                    if (state.vignette > 0)
                      IgnorePointer(
                        child: Container(
                          decoration: BoxDecoration(
                            gradient: RadialGradient(
                              radius: 0.85,
                              colors: [
                                Colors.transparent,
                                Colors.black.withValues(alpha: (state.vignette * 0.8).clamp(0.0, 0.9)),
                              ],
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),

          // Tap to Play / Pause gesture
          Positioned.fill(
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: state.togglePlay,
                child: Center(
                  child: AnimatedOpacity(
                    opacity: state.isPlaying ? 0.0 : 0.85,
                    duration: const Duration(milliseconds: 200),
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: const BoxDecoration(
                        color: Colors.black54,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.play_arrow_rounded,
                        size: 40,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
