import 'package:flutter_test/flutter_test.dart';
import 'package:videocut_mobile/main.dart';

void main() {
  testWidgets('VideoCut mobile editor loads smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const VideoCutApp());
    expect(find.text('VideoCut Mobile'), findsNWidgets(2));
    expect(find.text('Export'), findsOneWidget);
    expect(find.text('Split'), findsAtLeast(1));
  });
}
