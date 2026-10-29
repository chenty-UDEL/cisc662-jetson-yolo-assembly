# CISC 662 — Jetson YOLO source and assembly submission

Tianyang Chen

Verified artifact version: [`bc6a3a2`](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/tree/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b).

This submission compares compiler-generated x86-64 and ARMv8-A (AArch64) assembly for a C reference implementation of the Jetson YOLO project's image preprocessing: BGR uint8 HWC to RGB FP32 CHW with normalization by 255.

- [Project repository](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly)
- [C source corresponding to both assembly files](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/blob/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b/src/preprocess_core.c)
- [x86-64 assembly](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/blob/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b/assembly/preprocess_x86_64.s)
- [ARMv8-A / AArch64 assembly](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/blob/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b/assembly/preprocess_armv8_aarch64.s)
- [Compare and contrast — English](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/blob/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b/COMPARE_EN.md)
- [Original Jetson YOLO benchmark source](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/tree/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b/original_project/src)
- [对照说明 — 中文](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly/blob/bc6a3a28bb526ef2a06819bd0a3c84c0ac3f190b/COMPARE_ZH.md)

The comparison covers argument registers, channel loads, integer-to-FP32 conversion, division, memory addressing, loop control and machine-code size. Both assembly outputs passed six functional emulation cases, including a 640×640 input. Compilation and verification records are included in the repository.
