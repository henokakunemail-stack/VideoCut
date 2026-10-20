import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'ui/editor_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: Color(0xFF161616),
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );
  runApp(const VideoCutApp());
}

class VideoCutApp extends StatelessWidget {
  const VideoCutApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VideoCut',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF101010),
        primaryColor: const Color(0xFF00E5FF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00E5FF),
          secondary: Color(0xFF00B0FF),
          surface: Color(0xFF1E1E1E),
        ),
      ),
      home: const EditorScreen(),
    );
  }
}
