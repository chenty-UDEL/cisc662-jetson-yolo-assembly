# x86-64 与 ARMv8-A 预处理汇编对比

Tianyang Chen · CISC 662 Computer Architecture

## 与 Jetson YOLO 项目的关系

原始 [benchmark.py](original_project/src/benchmark.py) 的 `step()` 先执行 LetterBox，再完成 BGR→RGB、HWC→CHW、浮点转换和除以 255。本次新增的 [C 参考函数](src/preprocess_core.c) 对应 LetterBox 之后的颜色、布局及 FP32 归一化计算，两份汇编都由这份 C 源码实际编译生成。原来的 Python/GPU 实验及测量结果保持不变。

设图像有 N 个像素，C 源码第 19–21 行分别计算：

```c
rgb_chw[i]       = (float)bgr[3*i + 2] / 255.0f;  // R
rgb_chw[N + i]   = (float)bgr[3*i + 1] / 255.0f;  // G
rgb_chw[2*N + i] = (float)bgr[3*i]     / 255.0f;  // B
```

输入是交错排列的 BGR 字节，输出是依次存放 R、G、B 三个平面的 FP32 数据。每个像素读取三个字节，执行三次转换、三次除法、三次浮点写入，工作量为 O(N)。该函数不包含缩放、CUDA 传输、批次维度、模型推理和 NMS。原实验的 TensorRT 输入绑定为 FP32，FP16 用于引擎内部计算，见 [engine_compatibility.json](original_project/engine_compatibility.json)。

## 编译方法

在当前 Windows 电脑上使用 Zig 0.15.2 附带的 Clang 20.1.2，采用 C11、`-O2`、`-mcpu=baseline`，目标分别为 `x86_64-linux-gnu` 和 `aarch64-linux-gnu`。为便于逐项对照，关闭循环向量化、SLP 向量化和循环展开，关闭浮点收缩，不启用 fast-math。完整命令保存在 [build_record.json](build_record.json)。

使用 `-S` 生成汇编，再把提交的 `.s` 文件汇编、链接后验证。编译方法参考 Clang 的[命令说明](https://clang.llvm.org/docs/CommandGuide/clang.html)、[交叉编译说明](https://clang.llvm.org/docs/CrossCompilation.html)及 Zig 的[工具链介绍](https://ziglang.org/learn/overview/)。

## 实际指令对比

| 操作 | x86-64 | ARMv8-A / AArch64 |
|---|---|---|
| 输入地址、输出地址、像素数 | `rdi`、`rsi`、`rdx` | `x0`、`x1`、`x2` |
| 判断像素数为零 | `test` + `je` | `cbz` |
| 读取无符号通道字节 | `movzx ecx, byte ptr [...]` | `ldr b1`、`ldur b2/b3` |
| 转换为 FP32 | `cvtsi2ss`，输入值为 0–255 | `ucvtf`，使用标量 `s` 寄存器 |
| 除以 255 | `divss` | `fdiv` |
| 写入三个输出平面 | `movss`，偏移为 0、`4*N`、`8*N` 字节 | `str`，通过移位或预先计算的寄存器形成相同偏移 |
| 移动到下个像素 | 输入地址 +3，输出地址 +4 | 输入地址 +3，输出地址 +4 |
| 循环计数 | `rax` 减一，再 `jne` | `subs x10, x10, #1`，再 `b.ne` |
| 取得 255.0f 常量 | 从只读常量区进行 RIP 相对加载 | 构造位模式 `0x437f0000`，再 `fmov` 到浮点寄存器 |
| 本次生成的函数栈操作 | 保存、恢复 `rbp` | 叶函数，不建立栈帧 |

红色通道在 x86-64 上对应 `movzx → cvtsi2ss → divss → movss`，在 AArch64 上对应 `ldr b1 → ucvtf s1, s1 → fdiv s1, s1, s0 → str s1`。编译器在其中穿插了其他通道的指令。Arm 的字节加载会清零寄存器的较高位，随后 `ucvtf` 将通道整数转换为浮点数。AArch64 参数寄存器约定见 [AAPCS64](https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst)。

两份代码均逐像素进行标量计算；使用 XMM 或 Arm FP/SIMD 寄存器，不代表本次代码已同时处理多个像素。

## 代码规模与验证

| 指标 | x86-64 | ARMv8-A / AArch64 |
|---|---:|---:|
| 函数机器码长度 | 106 字节 | 92 字节 |
| 静态解码指令数 | 29 | 23 |
| 实际出现的指令长度 | 1、2、3、4、5、8 字节 | 均为 4 字节 |

x86-64 的计数包含一条对齐 NOP。统计范围是函数符号内部，不包含外部常量和调试信息。指令更少、代码更短不能直接推出实际运行更快。

Windows x86-64 原生 C 测试通过。两份提交汇编还经过汇编、链接及 Unicorn 指令模拟执行，均通过六组检查：零像素及空指针、单像素、区分颜色顺序的双像素、全部 256 个字节值、奇数长度随机输入、640×640 随机输入。两种架构的输出均与独立 Python FP32 参考结果逐项一致，输出边界保护值保持不变。完整尺寸的一组检查了每种架构的 1,228,800 个通道值。

验证结果见 [assembly_tests.json](verification/assembly_tests.json)，机器码和反汇编见 [disassembly/](disassembly/)。模拟执行用于核对功能，不用于测量 Jetson 性能。

两种架构实现了相同的预处理算法，差异体现在参数寄存器、整数到浮点的转换方式、寻址方式、循环控制和指令编码。项目的 PyTorch 与 TensorRT 加速结论仍来自已经完成的 Jetson GPU 实验。
