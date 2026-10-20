import 'package:flutter_test/flutter_test.dart';
import 'package:videocut_mobile/editor_state.dart';
import 'package:videocut_mobile/main.dart';

void main() {
  testWidgets('VideoCut mobile editor loads smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const VideoCutApp());
    expect(find.text('VideoCut Mobile'), findsNWidgets(2));
    expect(find.text('Export'), findsOneWidget);
    expect(find.text('Split'), findsAtLeast(1));
  });

  test('EditorState pause and playback lifecycle test', () {
    final state = EditorState();
    expect(state.isPlaying, isFalse);
    state.togglePlay();
    expect(state.isPlaying, isTrue);
    state.pause();
    expect(state.isPlaying, isFalse);
    state.dispose();
  });

  test('EditorState splitActiveClip creates right segment', () {
    final state = EditorState();
    final initialCount = state.videoClips.length;
    state.seek(2000);
    state.splitActiveClip();
    expect(state.videoClips.length, equals(initialCount + 1));
    state.dispose();
  });
}
