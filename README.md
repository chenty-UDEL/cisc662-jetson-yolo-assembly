# Jetson YOLO project: source and CPU assembly supplement

Tianyang Chen · CISC 662 Computer Architecture

Repository: [chenty-UDEL/cisc662-jetson-yolo-assembly](https://github.com/chenty-UDEL/cisc662-jetson-yolo-assembly). Direct submission links are collected in [SUBMISSION.md](SUBMISSION.md).

This package supplies a C preprocessing reference, its compiler-generated x86-64 and ARMv8-A (AArch64) assembly, and a comparison of the two outputs. The reference implements the color conversion, channel layout and FP32 normalization math in the original Jetson YOLO benchmark. It is a new CPU reference; the measured YOLO experiment uses Python, NumPy, PyTorch and TensorRT on the GPU.

## Files to submit

| Item | File |
|---|---|
| C source corresponding to both assembly files | [src/preprocess_core.c](src/preprocess_core.c) |
| C interface and buffer contract | [src/preprocess_core.h](src/preprocess_core.h) |
| x86-64 assembly, Linux System V ABI | [assembly/preprocess_x86_64.s](assembly/preprocess_x86_64.s) |
| ARMv8-A assembly, AArch64 Linux ABI | [assembly/preprocess_armv8_aarch64.s](assembly/preprocess_armv8_aarch64.s) |
| Compare and contrast, English | [COMPARE_EN.md](COMPARE_EN.md) |
| 对照说明，中文 | [COMPARE_ZH.md](COMPARE_ZH.md) |
| Original experiment source | [original_project/src/benchmark.py](original_project/src/benchmark.py) and companion scripts in that directory |

Submit the C source, both `.s` files and `COMPARE_EN.md` using the links in [SUBMISSION.md](SUBMISSION.md). Use links pinned to the submitted commit when recording the final submission. The original Python source provides the project context.

## Reproduce on this Windows computer

Requirements: Python 3, the Windows x86-64 distribution of [Zig 0.15.2](https://ziglang.org/download/), and the optional verification dependencies below. The compiler is not included in the submission archive.

Extract Zig to `.tools/zig-x86_64-windows-0.15.2/`, then run from this folder:

```powershell
python build.py
python test_reference.py
python -m pip install --target .runtime/python -r requirements-verification.txt
python verify_assembly.py
```

Alternatively, pass a compiler path with `python build.py --zig C:/path/to/zig.exe`. The C-to-assembly commands are recorded in [build_record.json](build_record.json). The Linux objects are assembled from the submitted `.s` files, then linked into small ELF files for functional emulation. Those ELF files expose a function entry for the emulator and are not standalone command-line programs.

The native test loads a Windows x86-64 DLL. The optional assembly test executes both Linux functions in Unicorn and records their disassembly using Capstone. It checks functional results, not hardware speed. No Jetson connection is needed for these supplementary checks.

## Provenance and verification

- [source_provenance.json](source_provenance.json): hashes for the C reference and byte-identical copies of the original Python scripts. `benchmark.py` and `common.py` also match the original experiment's execution identity.
- [verification/reference_tests.json](verification/reference_tests.json): native C correctness checks.
- [verification/assembly_tests.json](verification/assembly_tests.json): x86-64 and ARMv8-A emulation results and actual code sizes.
- [disassembly/](disassembly/): instruction bytes decoded from the linked ELF functions.
- [compiler_download.json](compiler_download.json): official compiler archive URL and verified SHA-256.
- `SHA256SUMS`: file hashes for the submission package.

The original experiment source is retained for inspection. Rerunning that full benchmark additionally requires its Jetson software environment, model files, input images and experiment metadata; those large experiment assets are retained in the existing project archive.

中文：本仓库包含源码、两种 CPU 汇编、中英文对照说明及验证记录。汇编对应新增的预处理 C 参考函数。可直接使用 [SUBMISSION.md](SUBMISSION.md) 中的链接提交。
