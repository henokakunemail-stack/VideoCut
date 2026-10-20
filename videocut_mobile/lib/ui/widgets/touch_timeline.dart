import 'package:flutter/material.dart';
import '../../editor_state.dart';

class TouchTimeline extends StatelessWidget {
  final EditorState state;

  const TouchTimeline({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final centerOffset = screenWidth / 2;
    // 100 pixels represents 1 second at zoom 1.0
    final pxPerMs = 0.08 * state.timelineZoom;

    return Container(
      height: 180,
      color: const Color(0xFF141414),
      child: Column(
        children: [
          // Timeline Sub-Bar: Timecode, Play button, Quick Split
          Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: const BoxDecoration(
              color: Color(0xFF1B1B1B),
              border: Border(bottom: BorderSide(color: Color(0xFF2A2A2A), width: 1)),
            ),
            child: Row(
              children: [
                Text(
                  state.formatTime(state.currentTimeMs),
                  style: const TextStyle(
                    color: Color(0xFF00E5FF),
                    fontWeight: FontWeight.bold,
                    fontFamily: 'monospace',
                    fontSize: 14,
                  ),
                ),
                Text(
                  ' / ${state.formatTime(state.totalDurationMs)}',
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
                const Spacer(),
                // Play / Pause toggle button
                IconButton(
                  icon: Icon(
                    state.isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    color: Colors.white,
                    size: 24,
                  ),
                  tooltip: state.isPlaying ? 'Pause' : 'Play',
                  onPressed: state.togglePlay,
                ),
                const SizedBox(width: 8),
                // Quick Split Button
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFF00E5FF), width: 1.2),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  icon: const Icon(Icons.content_cut_rounded, size: 14, color: Color(0xFF00E5FF)),
                  label: const Text(
                    'Split',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                  onPressed: state.splitActiveClip,
                ),
              ],
            ),
          ),

          // Multi-Track Interactive Touch Scroll View
          Expanded(
            child: GestureDetector(
              onHorizontalDragUpdate: (details) {
                // Dragging moves the timeline under the playhead
                final deltaMs = (-details.primaryDelta! / pxPerMs).round();
                state.seek(state.currentTimeMs + deltaMs);
              },
              onScaleUpdate: (details) {
                if (details.scale != 1.0) {
                  state.setZoom(state.timelineZoom * details.scale);
                }
              },
              child: Stack(
                alignment: Alignment.centerLeft,
                children: [
                  // Timeline ruler + tracks container
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    physics: const NeverScrollableScrollPhysics(),
                    child: Container(
                      padding: EdgeInsets.only(left: centerOffset, right: centerOffset),
                      transform: Matrix4.translationValues(-state.currentTimeMs * pxPerMs, 0, 0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // 1. Timecode Ruler
                          _buildRuler(pxPerMs, state.totalDurationMs),

                          const SizedBox(height: 4),

                          // 2. Video Track
                          SizedBox(
                            height: 44,
                            child: Row(
                              children: state.videoClips.map((clip) {
                                final isSelected = clip.id == state.selectedClipId;
                                final width = clip.durationMs * pxPerMs;
                                return GestureDetector(
                                  onTap: () => state.selectClip(clip.id),
                                  child: Container(
                                    width: width,
                                    margin: const EdgeInsets.symmetric(horizontal: 1),
                                    decoration: BoxDecoration(
                                      color: clip.color,
                                      borderRadius: BorderRadius.circular(4),
                                      border: isSelected
                                          ? Border.all(color: const Color(0xFF00E5FF), width: 2)
                                          : Border.all(color: Colors.white24, width: 0.5),
                                    ),
                                    alignment: Alignment.centerLeft,
                                    padding: const EdgeInsets.symmetric(horizontal: 6),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.movie_creation_outlined, size: 14, color: Colors.white70),
                                        const SizedBox(width: 4),
                                        Expanded(
                                          child: Text(
                                            clip.title,
                                            style: const TextStyle(
                                              color: Colors.white,
                                              fontSize: 11,
                                              fontWeight: FontWeight.w600,
                                            ),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                        Text(
                                          '${(clip.durationMs / 1000).toStringAsFixed(1)}s',
                                          style: const TextStyle(color: Colors.white60, fontSize: 10),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),

                          const SizedBox(height: 4),

                          // 3. Audio Track
                          SizedBox(
                            height: 28,
                            child: Row(
                              children: state.audioClips.map((clip) {
                                final width = clip.durationMs * pxPerMs;
                                return Container(
                                  width: width,
                                  decoration: BoxDecoration(
                                    color: clip.color.withValues(alpha: 0.85),
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  padding: const EdgeInsets.symmetric(horizontal: 6),
                                  alignment: Alignment.centerLeft,
                                  child: Row(
                                    children: [
                                      const Icon(Icons.music_note_rounded, size: 12, color: Colors.white),
                                      const SizedBox(width: 4),
                                      Expanded(
                                        child: Text(
                                          clip.title,
                                          style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w500),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }).toList(),
                            ),
                          ),

                          const SizedBox(height: 4),

                          // 4. Text Subtitle Track
                          SizedBox(
                            height: 24,
                            child: Row(
                              children: state.textClips.map((clip) {
                                final width = clip.durationMs * pxPerMs;
                                return Container(
                                  width: width,
                                  margin: EdgeInsets.only(left: clip.startMs == 0 ? 0 : (clip.startMs * pxPerMs * 0.1)),
                                  decoration: BoxDecoration(
                                    color: clip.color.withValues(alpha: 0.8),
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  padding: const EdgeInsets.symmetric(horizontal: 6),
                                  alignment: Alignment.centerLeft,
                                  child: Row(
                                    children: [
                                      const Icon(Icons.title_rounded, size: 11, color: Colors.white),
                                      const SizedBox(width: 4),
                                      Expanded(
                                        child: Text(
                                          clip.title,
                                          style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Fixed Center Playhead Marker
                  Positioned(
                    left: centerOffset - 1,
                    top: 0,
                    bottom: 0,
                    child: Column(
                      children: [
                        // Playhead head icon
                        Container(
                          width: 10,
                          height: 10,
                          decoration: const BoxDecoration(
                            color: Color(0xFF00E5FF),
                            shape: BoxShape.circle,
                          ),
                        ),
                        // Vertical indicator line
                        Expanded(
                          child: Container(
                            width: 2,
                            color: const Color(0xFF00E5FF),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRuler(double pxPerMs, int totalDurationMs) {
    final totalSeconds = (totalDurationMs / 1000).ceil() + 2;
    return SizedBox(
      height: 20,
      child: Row(
        children: List.generate(totalSeconds, (sec) {
          final width = 1000 * pxPerMs;
          return SizedBox(
            width: width,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Container(width: 1, height: 10, color: Colors.white38),
                const SizedBox(width: 3),
                Text(
                  '${sec}s',
                  style: const TextStyle(color: Colors.white38, fontSize: 9, fontFamily: 'monospace'),
                ),
                const Spacer(),
                Container(width: 1, height: 5, color: Colors.white24),
                const Spacer(),
              ],
            ),
          );
        }),
      ),
    );
  }
}
