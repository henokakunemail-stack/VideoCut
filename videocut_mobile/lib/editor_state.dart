import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';

enum AspectRatioMode { ratio9_16, ratio16_9, ratio1_1, ratio4_5 }
enum ToolTab { root, edit, audio, text, adjust, canvas, effects }

class ClipItem {
  final String id;
  String title;
  int startMs;
  int durationMs;
  Color color;
  double speed;
  double volume;

  ClipItem({
    required this.id,
    required this.title,
    required this.startMs,
    required this.durationMs,
    required this.color,
    this.speed = 1.0,
    this.volume = 1.0,
  });

  ClipItem copyWith({
    String? title,
    int? startMs,
    int? durationMs,
    Color? color,
    double? speed,
    double? volume,
  }) {
    return ClipItem(
      id: id,
      title: title ?? this.title,
      startMs: startMs ?? this.startMs,
      durationMs: durationMs ?? this.durationMs,
      color: color ?? this.color,
      speed: speed ?? this.speed,
      volume: volume ?? this.volume,
    );
  }
}

class EditorState extends ChangeNotifier {
  bool _disposed = false;
  int currentTimeMs = 0;
  bool isPlaying = false;
  Timer? _playbackTimer;

  @override
  void notifyListeners() {
    if (_disposed) return;
    super.notifyListeners();
  }

  void pause() {
    if (isPlaying) {
      isPlaying = false;
      _playbackTimer?.cancel();
      _playbackTimer = null;
      notifyListeners();
    }
  }

  double timelineZoom = 1.0;
  AspectRatioMode aspectRatio = AspectRatioMode.ratio9_16;
  ToolTab currentTab = ToolTab.root;

  // Visual adjustments (-1.0 to 1.0 or scale)
  double brightness = 0.0;
  double contrast = 1.0;
  double saturation = 1.0;
  double temperature = 0.0;
  double vignette = 0.0;

  // Tracks
  List<ClipItem> videoClips = [
    ClipItem(id: 'c1', title: 'Intro_Shot.mp4', startMs: 0, durationMs: 4000, color: const Color(0xFF2C3E50)),
    ClipItem(id: 'c2', title: 'Main_Scene.mp4', startMs: 4000, durationMs: 6000, color: const Color(0xFF16A085)),
    ClipItem(id: 'c3', title: 'Action_Beat.mp4', startMs: 10000, durationMs: 4000, color: const Color(0xFF8E44AD)),
  ];

  List<ClipItem> audioClips = [
    ClipItem(id: 'a1', title: 'Cinematic_Beats.mp3', startMs: 0, durationMs: 14000, color: const Color(0xFFD35400)),
  ];

  List<ClipItem> textClips = [
    ClipItem(id: 't1', title: 'VideoCut Mobile', startMs: 1000, durationMs: 3500, color: const Color(0xFF2980B9)),
    ClipItem(id: 't2', title: 'CapCut Alternative', startMs: 5000, durationMs: 4000, color: const Color(0xFF27AE60)),
  ];

  String? selectedClipId = 'c1';

  int get totalDurationMs {
    int maxEnd = 14000;
    for (final c in videoClips) {
      maxEnd = max(maxEnd, c.startMs + c.durationMs);
    }
    return maxEnd;
  }

  void seek(int ms) {
    currentTimeMs = ms.clamp(0, totalDurationMs);
    notifyListeners();
  }

  void togglePlay() {
    isPlaying = !isPlaying;
    if (isPlaying) {
      _playbackTimer?.cancel();
      _playbackTimer = Timer.periodic(const Duration(milliseconds: 33), (timer) {
        if (currentTimeMs >= totalDurationMs) {
          currentTimeMs = 0;
        } else {
          currentTimeMs += 33;
        }
        notifyListeners();
      });
    } else {
      _playbackTimer?.cancel();
    }
    notifyListeners();
  }

  void setAspectRatio(AspectRatioMode mode) {
    aspectRatio = mode;
    notifyListeners();
  }

  void setTab(ToolTab tab) {
    currentTab = tab;
    notifyListeners();
  }

  void setZoom(double zoom) {
    timelineZoom = zoom.clamp(0.5, 3.0);
    notifyListeners();
  }

  void selectClip(String? id) {
    selectedClipId = id;
    notifyListeners();
  }

  void splitActiveClip() {
    final idx = videoClips.indexWhere((c) =>
        c.startMs <= currentTimeMs && (c.startMs + c.durationMs) > currentTimeMs);
    if (idx == -1) return;

    final target = videoClips[idx];
    final leftDuration = currentTimeMs - target.startMs;
    final rightDuration = target.durationMs - leftDuration;
    if (leftDuration < 200 || rightDuration < 200) return;

    final left = target.copyWith(durationMs: leftDuration);
    final right = ClipItem(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      title: '${target.title}_part',
      startMs: currentTimeMs,
      durationMs: rightDuration,
      color: target.color.withValues(alpha: 0.8),
      speed: target.speed,
      volume: target.volume,
    );

    videoClips.removeAt(idx);
    videoClips.insert(idx, left);
    videoClips.insert(idx + 1, right);
    selectedClipId = right.id;
    notifyListeners();
  }

  void deleteActiveClip() {
    if (selectedClipId == null || videoClips.length <= 1) return;
    videoClips.removeWhere((c) => c.id == selectedClipId);
    selectedClipId = videoClips.first.id;
    notifyListeners();
  }

  void setClipSpeed(double speed) {
    if (selectedClipId == null) return;
    final idx = videoClips.indexWhere((c) => c.id == selectedClipId);
    if (idx != -1) {
      videoClips[idx].speed = speed;
      notifyListeners();
    }
  }

  void setClipVolume(double vol) {
    if (selectedClipId == null) return;
    final idx = videoClips.indexWhere((c) => c.id == selectedClipId);
    if (idx != -1) {
      videoClips[idx].volume = vol;
      notifyListeners();
    }
  }

  void resetAdjustments() {
    brightness = 0.0;
    contrast = 1.0;
    saturation = 1.0;
    temperature = 0.0;
    vignette = 0.0;
    notifyListeners();
  }

  String formatTime(int ms) {
    final totalSec = ms ~/ 1000;
    final minutes = (totalSec ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSec % 60).toString().padLeft(2, '0');
    final frames = ((ms % 1000) ~/ 33).toString().padLeft(2, '0');
    return '$minutes:$seconds:$frames';
  }

  @override
  void dispose() {
    _disposed = true;
    _playbackTimer?.cancel();
    _playbackTimer = null;
    super.dispose();
  }
}
