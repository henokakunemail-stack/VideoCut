# CapCut 9.6.0.4097 — feature research (names only)

Method: printable-string scan (read-only) of `VECreator.dll`, `videoeditor.dll`, `cccreator.dll`.
No code, assets, LUTs, models or shaders copied. Reimplementations are original and open-source based.
Ghidra/REA deep-dive not yet run (needs MCP reconnect); string scan is enough for the feature list.

## Feature identifiers found

| Area | Identifiers | VideoCut phase |
|---|---|---|
| Color | `adjust_lut`, `adjust_color_wheel`, `adjust_color_curves`, `adjust_hsl_basics`, `curve-hsl` (HSL curves), `adjust_sharpen`, `pc_import_luts` | 2 |
| Scopes/relight | `SmartRelight`, `retouch` presets | 2 / 4 |
| Speed | `video_tab_speed_normal/_curve/_velocity`, `curvespeed`, `SmoothSlowMotion`, `optical_flow` (`MotionInterpolationAnchorPoint`) | 3 |
| Stabilize | `videoStabilize`, `anti-shake` (+`anti_shake_level`) | 3 |
| Keyframes | `adjust_keyframe(s)`, `QmlKeyframe`, text-curve keyframes | 3 |
| Matting | `ChromaMatting`, `CustomMatting`, `IntelligentMatting`, `video_tab_matting` | 1 done / 4 |
| Beauty | `video_tab_beauty_face/_body/_hair` + presets | existing, extend |
| AI video | `SuperResolution` (`upscale_resolution`), `video_denoise` (`vip_feature_video_denoise`), `auto_reframe` | 4 |
| AI audio | `AudioDenoise`, `VocalSeparation`, `VocalBeautify` (`vip_feature_vocal_*`), `isolate_voice` | 4 |
| Captions | `Caption`, `bilingual_captions` | 4 |

## Notes
- HSL exists as both basic sliders and *HSL curves*; color wheels include a "log" variant (`adjust_log_color_wheels_score`).
- Pro gating uses `vip.vip_feature_*` flags and server-side checks. Cloud/account features (templates, cloud effects, sync) are out of scope.
- Parameter ranges are not recoverable from strings; VideoCut uses standard ranges (-100..100).
