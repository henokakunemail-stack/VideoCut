import 'package:flutter/material.dart';
import '../editor_state.dart';
import 'widgets/top_header.dart';
import 'widgets/preview_canvas.dart';
import 'widgets/touch_timeline.dart';
import 'widgets/bottom_tool_bar.dart';

class EditorScreen extends StatefulWidget {
  const EditorScreen({super.key});

  @override
  State<EditorScreen> createState() => _EditorScreenState();
}

class _EditorScreenState extends State<EditorScreen> {
  late final EditorState _editorState;
  String _selectedResolution = '1080P';

  @override
  void initState() {
    super.initState();
    _editorState = EditorState();
  }

  @override
  void dispose() {
    _editorState.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _editorState,
      builder: (context, _) {
        return Scaffold(
          backgroundColor: const Color(0xFF101010),
          body: SafeArea(
            child: Column(
              children: [
                // 1. Top Header (Project Title, Resolution, Export button)
                TopHeader(
                  state: _editorState,
                  selectedResolution: _selectedResolution,
                  onResolutionChanged: (res) {
                    setState(() => _selectedResolution = res);
                  },
                ),

                // 2. Video Preview Viewport
                Expanded(
                  child: PreviewCanvas(state: _editorState),
                ),

                // 3. Multi-Track Touch Timeline
                TouchTimeline(state: _editorState),

                // 4. Bottom Action Tools & Sub-Bars
                BottomToolBar(state: _editorState),
              ],
            ),
          ),
        );
      },
    );
  }
}
