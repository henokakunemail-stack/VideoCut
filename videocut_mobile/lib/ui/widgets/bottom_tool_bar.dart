import 'package:flutter/material.dart';
import '../../editor_state.dart';

class BottomToolBar extends StatelessWidget {
  final EditorState state;

  const BottomToolBar({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF161616),
        border: Border(top: BorderSide(color: Color(0xFF262626), width: 1)),
      ),
      child: SafeArea(
        top: false,
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 200),
          child: _buildCurrentPanel(context),
        ),
      ),
    );
  }

  Widget _buildCurrentPanel(BuildContext context) {
    switch (state.currentTab) {
      case ToolTab.root:
        return _buildRootBar();
      case ToolTab.edit:
        return _buildEditSubBar(context);
      case ToolTab.adjust:
        return _buildAdjustSubBar();
      case ToolTab.canvas:
        return _buildCanvasSubBar();
      case ToolTab.audio:
        return _buildAudioSubBar(context);
      case ToolTab.text:
        return _buildTextSubBar(context);
      case ToolTab.effects:
        return _buildEffectsSubBar(context);
    }
  }

  // Root Bar: 6 Core Mobile Tools
  Widget _buildRootBar() {
    return SizedBox(
      height: 64,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildToolItem(Icons.content_cut_rounded, 'Edit', () => state.setTab(ToolTab.edit)),
          _buildToolItem(Icons.music_note_rounded, 'Audio', () => state.setTab(ToolTab.audio)),
          _buildToolItem(Icons.title_rounded, 'Text', () => state.setTab(ToolTab.text)),
          _buildToolItem(Icons.tune_rounded, 'Adjust', () => state.setTab(ToolTab.adjust)),
          _buildToolItem(Icons.aspect_ratio_rounded, 'Ratio', () => state.setTab(ToolTab.canvas)),
          _buildToolItem(Icons.auto_awesome_rounded, 'Effects', () => state.setTab(ToolTab.effects)),
        ],
      ),
    );
  }

  Widget _buildToolItem(IconData icon, String label, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        constraints: const BoxConstraints(minWidth: 54, minHeight: 56),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 22, color: Colors.white),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
          ],
        ),
      ),
    );
  }

  // Sub-Bar: Edit (Split, Speed, Volume, Delete)
  Widget _buildEditSubBar(BuildContext context) {
    final activeClip = state.videoClips.cast<ClipItem?>().firstWhere(
          (c) => c?.id == state.selectedClipId,
          orElse: () => null,
        );

    return Container(
      height: 70,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          IconButton(
            icon: const Icon(Icons.close_rounded, color: Colors.white60),
            onPressed: () => state.setTab(ToolTab.root),
          ),
          _buildToolItem(Icons.content_cut_rounded, 'Split', state.splitActiveClip),
          // Speed dialog/slider button
          _buildToolItem(Icons.speed_rounded, '${activeClip?.speed.toStringAsFixed(1) ?? "1.0"}x', () {
            _showSpeedDialog(context, activeClip);
          }),
          // Volume dialog/slider button
          _buildToolItem(Icons.volume_up_rounded, 'Volume', () {
            _showVolumeDialog(context, activeClip);
          }),
          _buildToolItem(Icons.delete_outline_rounded, 'Delete', state.deleteActiveClip),
        ],
      ),
    );
  }

  // Sub-Bar: Adjust (Brightness, Contrast, Saturation, Vignette)
  Widget _buildAdjustSubBar() {
    return Container(
      height: 80,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18, color: Colors.white60),
            onPressed: () => state.setTab(ToolTab.root),
          ),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildSliderControl(
                    'Brightness',
                    state.brightness,
                    -0.5,
                    0.5,
                    (val) {
                      state.brightness = val;
                      state.seek(state.currentTimeMs);
                    },
                  ),
                  _buildSliderControl(
                    'Contrast',
                    state.contrast,
                    0.5,
                    2.0,
                    (val) {
                      state.contrast = val;
                      state.seek(state.currentTimeMs);
                    },
                  ),
                  _buildSliderControl(
                    'Vignette',
                    state.vignette,
                    0.0,
                    1.0,
                    (val) {
                      state.vignette = val;
                      state.seek(state.currentTimeMs);
                    },
                  ),
                ],
              ),
            ),
          ),
          TextButton(
            onPressed: state.resetAdjustments,
            child: const Text('Reset', style: TextStyle(color: Color(0xFF00E5FF), fontSize: 12)),
          ),
        ],
      ),
    );
  }

  Widget _buildSliderControl(String label, double value, double min, double max, ValueChanged<double> onChanged) {
    return Container(
      width: 140,
      margin: const EdgeInsets.symmetric(horizontal: 4),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text('$label: ${value.toStringAsFixed(2)}', style: const TextStyle(color: Colors.white70, fontSize: 11)),
          SliderTheme(
            data: SliderThemeData(
              activeTrackColor: const Color(0xFF00E5FF),
              inactiveTrackColor: Colors.white24,
              thumbColor: Colors.white,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
              trackHeight: 2,
            ),
            child: Slider(
              value: value.clamp(min, max),
              min: min,
              max: max,
              onChanged: onChanged,
            ),
          ),
        ],
      ),
    );
  }

  // Sub-Bar: Canvas Aspect Ratio (9:16, 16:9, 1:1, 4:5)
  Widget _buildCanvasSubBar() {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18, color: Colors.white60),
            onPressed: () => state.setTab(ToolTab.root),
          ),
          _buildRatioChip('9:16 (TikTok)', AspectRatioMode.ratio9_16),
          _buildRatioChip('16:9 (YT)', AspectRatioMode.ratio16_9),
          _buildRatioChip('1:1', AspectRatioMode.ratio1_1),
          _buildRatioChip('4:5', AspectRatioMode.ratio4_5),
        ],
      ),
    );
  }

  Widget _buildRatioChip(String label, AspectRatioMode mode) {
    final isSelected = state.aspectRatio == mode;
    return ChoiceChip(
      label: Text(label, style: TextStyle(color: isSelected ? Colors.black : Colors.white, fontSize: 11)),
      selected: isSelected,
      selectedColor: const Color(0xFF00E5FF),
      backgroundColor: const Color(0xFF262626),
      onSelected: (val) {
        if (val) state.setAspectRatio(mode);
      },
    );
  }

  // Sub-Bar: Audio (BGM, Voiceover, Denoise)
  Widget _buildAudioSubBar(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18, color: Colors.white60),
            onPressed: () => state.setTab(ToolTab.root),
          ),
          _buildToolItem(Icons.library_music_rounded, 'BGM', () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Audio BGM aktif.')),
            );
          }),
          _buildToolItem(Icons.mic_rounded, 'Record', () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Voiceover recorder standby.')),
            );
          }),
          _buildToolItem(Icons.noise_control_off_rounded, 'Denoise', () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('AI Noise reduction diterapkan pada audio.')),
            );
          }),
        ],
      ),
    );
  }

  // Sub-Bar: Text & Subtitle
  Widget _buildTextSubBar(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18, color: Colors.white60),
            onPressed: () => state.setTab(ToolTab.root),
          ),
          _buildToolItem(Icons.text_fields_rounded, 'Add Text', () {
            state.textClips.add(
              ClipItem(
                id: DateTime.now().microsecondsSinceEpoch.toString(),
                title: 'Teks Baru',
                startMs: state.currentTimeMs,
                durationMs: 3000,
                color: const Color(0xFFE67E22),
              ),
            );
            state.seek(state.currentTimeMs);
          }),
          _buildToolItem(Icons.subtitles_rounded, 'Auto Caption', () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Auto Caption offline via Whisper model.')),
            );
          }),
        ],
      ),
    );
  }

  // Sub-Bar: Effects & Filters
  Widget _buildEffectsSubBar(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, size: 18, color: Colors.white60),
            onPressed: () => state.setTab(ToolTab.root),
          ),
          _buildToolItem(Icons.filter_b_and_w_rounded, 'B&W', () {
            state.saturation = 0.0;
            state.contrast = 1.3;
            state.seek(state.currentTimeMs);
          }),
          _buildToolItem(Icons.movie_filter_rounded, 'Cinematic', () {
            state.contrast = 1.25;
            state.brightness = -0.05;
            state.vignette = 0.35;
            state.seek(state.currentTimeMs);
          }),
          _buildToolItem(Icons.wb_sunny_rounded, 'Warm', () {
            state.brightness = 0.05;
            state.contrast = 1.1;
            state.vignette = 0.15;
            state.seek(state.currentTimeMs);
          }),
        ],
      ),
    );
  }

  void _showSpeedDialog(BuildContext context, ClipItem? clip) {
    if (clip == null) return;
    showDialog(
      context: context,
      builder: (ctx) {
        double currentSpeed = clip.speed;
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF262626),
              title: const Text('Speed Ramping', style: TextStyle(color: Colors.white, fontSize: 16)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('${currentSpeed.toStringAsFixed(1)}x',
                      style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 24, fontWeight: FontWeight.bold)),
                  Slider(
                    value: currentSpeed,
                    min: 0.2,
                    max: 4.0,
                    divisions: 19,
                    activeColor: const Color(0xFF00E5FF),
                    onChanged: (val) {
                      setDialogState(() => currentSpeed = val);
                      state.setClipSpeed(val);
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Selesai', style: TextStyle(color: Color(0xFF00E5FF))),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showVolumeDialog(BuildContext context, ClipItem? clip) {
    if (clip == null) return;
    showDialog(
      context: context,
      builder: (ctx) {
        double currentVol = clip.volume;
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF262626),
              title: const Text('Audio Volume', style: TextStyle(color: Colors.white, fontSize: 16)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('${(currentVol * 100).toInt()}%',
                      style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 24, fontWeight: FontWeight.bold)),
                  Slider(
                    value: currentVol,
                    min: 0.0,
                    max: 2.0,
                    activeColor: const Color(0xFF00E5FF),
                    onChanged: (val) {
                      setDialogState(() => currentVol = val);
                      state.setClipVolume(val);
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Selesai', style: TextStyle(color: Color(0xFF00E5FF))),
                ),
              ],
            );
          },
        );
      },
    );
  }
}
