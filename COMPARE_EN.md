# Compare and contrast: x86-64 and ARMv8-A preprocessing

Tianyang Chen · CISC 662 Computer Architecture

## Connection to the Jetson YOLO project

The original benchmark's `step()` function in [benchmark.py](original_project/src/benchmark.py) applies LetterBox, reverses BGR to RGB, changes HWC to CHW, converts the input tensor to floating point and divides by 255. The new [C reference](src/preprocess_core.c) implements the color/layout/FP32 normalization portion after LetterBox. Its two assembly files are CPU code generated from this C source. The original Python/GPU benchmark and its measured timings are unchanged.

For an already letterboxed image with `N` pixels, the reference writes:

```c
rgb_chw[i]       = (float)bgr[3*i + 2] / 255.0f;  // R
rgb_chw[N + i]   = (float)bgr[3*i + 1] / 255.0f;  // G
rgb_chw[2*N + i] = (float)bgr[3*i]     / 255.0f;  // B
```

The three statements are C source lines 19–21. The output contains three FP32 planes. Each pixel requires three byte loads, three conversions, three divisions and three float stores, with O(N) work. Resizing, CUDA transfer, batching, inference and NMS are outside this function. The recorded TensorRT input binding is FP32, while FP16 is enabled internally in the engine; see [engine_compatibility.json](original_project/engine_compatibility.json).

## Compilation

Both outputs use Zig 0.15.2's Clang 20.1.2 on Windows, C11, `-O2` and `-mcpu=baseline`. Their target triples are `x86_64-linux-gnu` and `aarch64-linux-gnu`. Loop vectorization, SLP vectorization and loop unrolling are disabled to make the scalar operation mapping easy to inspect. Floating-point contraction is disabled; fast-math is not enabled. Full commands and compiler identity are in [build_record.json](build_record.json).

The `.s` files are compiler outputs produced with `-S`; they are then assembled and linked for verification. Clang documents the assembly-output stage and target selection in its [command guide](https://clang.llvm.org/docs/CommandGuide/clang.html) and [cross-compilation guide](https://clang.llvm.org/docs/CrossCompilation.html). Zig supplies a cross-compiling C toolchain, described in its [overview](https://ziglang.org/learn/overview/).

## Observed similarities and differences

| Operation | x86-64 output | ARMv8-A / AArch64 output |
|---|---|---|
| Three arguments: input, output, N | `rdi`, `rsi`, `rdx` | `x0`, `x1`, `x2` |
| Zero-length input | `test rdx, rdx` then `je` | `cbz x2` |
| Read an unsigned channel byte | `movzx ecx, byte ptr [...]` | `ldr b1, [x9]` or `ldur b2/b3, [...]` |
| Convert to FP32 | `cvtsi2ss` into an XMM register; values are 0–255 | `ucvtf` using scalar `s` registers |
| Divide by 255 | Scalar `divss` | Scalar `fdiv` |
| Store the RGB planes | `movss` with offsets 0, `4*rdx`, `8*rdx` | `str s...` with offsets 0, `x2 << 2`, `x8` where `x8 = x2 << 3` |
| Advance to the next pixel | Input +3 bytes, output +4 bytes | Input +3 bytes, output +4 bytes |
| Counted loop | Decrement `rax`, branch with `jne` | `subs x10, x10, #1`, branch with `b.ne` |
| Constant 255.0f | Load from a nearby read-only constant using RIP-relative addressing | Materialize bits `0x437f0000` in `w10`, then `fmov s0, w10` |
| Function entry/exit in this build | Save/restore `rbp` using the stack | Leaf function with no stack frame |

For example, the red channel uses `movzx` → `cvtsi2ss` → `divss` → `movss` on x86-64, and `ldr b1` → `ucvtf s1, s1` → `fdiv s1, s1, s0` → `str s1` on AArch64. The compiler interleaves some green/blue instructions with these operations. AArch64's byte load into `b1` clears the higher register bits, allowing the following unsigned conversion to interpret the channel value correctly. AArch64's argument-register convention is specified by [AAPCS64](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst).

These are scalar calculations on both targets. The use of XMM or Arm FP/SIMD registers does not mean several pixels are processed per instruction in these outputs.

## Code size and correctness

Disassembling each linked function produced the following measurements:

| Measure | x86-64 | ARMv8-A / AArch64 |
|---|---:|---:|
| Function machine-code bytes | 106 | 92 |
| Static decoded instructions | 29 | 23 |
| Observed instruction sizes | 1, 2, 3, 4, 5, 8 bytes | 4 bytes |

The x86-64 count includes one alignment NOP. Sizes cover the function symbol, including padding within it, and exclude external constants and debug information. Instruction counts and code size describe this compiler output; they do not establish which processor runs the function faster.

The Windows x86-64 C build passed native checks. Both submitted assembly files were also assembled, linked and executed under Unicorn instruction emulation. All six cases passed on both targets: zero length with null pointers, one pixel, two pixels with distinct channel order, all 256 byte values, an odd-length random input and a 640×640 random input. Outputs matched an independent Python FP32 reference exactly and preserved output guard values. The full-size case checks 1,228,800 channel values per target. Results and tool versions are in [assembly_tests.json](verification/assembly_tests.json); decoded bytes are in [disassembly/](disassembly/).

Both architectures implement the same preprocessing math and memory layout. Their instruction selection, register use, addressing and code encoding differ. This supplement demonstrates those CPU-level differences; the project's PyTorch-versus-TensorRT speedup comes from the separately recorded Jetson GPU experiment.
