	.intel_syntax noprefix
	.file	"preprocess_core.c"
	.section	.rodata.cst4,"aM",@progbits,4
	.p2align	2, 0x0                          # -- Begin function yolo_bgr8_to_rgb_chw_f32
.LCPI0_0:
	.long	0x437f0000                      # float 255
	.text
	.globl	yolo_bgr8_to_rgb_chw_f32
	.p2align	4
	.type	yolo_bgr8_to_rgb_chw_f32,@function
yolo_bgr8_to_rgb_chw_f32:               # @yolo_bgr8_to_rgb_chw_f32
.Lfunc_begin0:
	.cfi_startproc
# %bb.0:
	.file	1 "." "src/preprocess_core.c"
	.loc	1 18 26 prologue_end            # src/preprocess_core.c:18:26
	test	rdx, rdx
	.loc	1 18 5 is_stmt 0                # src/preprocess_core.c:18:5
	je	.LBB0_4
# %bb.1:
	push	rbp
	.cfi_def_cfa_offset 16
	.cfi_offset rbp, -16
	mov	rbp, rsp
	.cfi_def_cfa_register rbp
	add	rdi, 2
	movss	xmm0, dword ptr [rip + .LCPI0_0] # xmm0 = [2.55E+2,0.0E+0,0.0E+0,0.0E+0]
	mov	rax, rdx
	.loc	1 0 5                           # :0:5
.Ltmp0:
	.p2align	4
.LBB0_2:                                # =>This Inner Loop Header: Depth=1
	.loc	1 19 29 is_stmt 1               # src/preprocess_core.c:19:29
	movzx	ecx, byte ptr [rdi]
	.loc	1 19 22 is_stmt 0               # src/preprocess_core.c:19:22
	xorps	xmm1, xmm1
	cvtsi2ss	xmm1, ecx
	.loc	1 19 44                         # src/preprocess_core.c:19:44
	divss	xmm1, xmm0
	.loc	1 20 43 is_stmt 1               # src/preprocess_core.c:20:43
	movzx	ecx, byte ptr [rdi - 1]
	.loc	1 20 36 is_stmt 0               # src/preprocess_core.c:20:36
	xorps	xmm2, xmm2
	cvtsi2ss	xmm2, ecx
	.loc	1 19 20 is_stmt 1               # src/preprocess_core.c:19:20
	movss	dword ptr [rsi], xmm1
	.loc	1 20 58                         # src/preprocess_core.c:20:58
	divss	xmm2, xmm0
	.loc	1 20 34 is_stmt 0               # src/preprocess_core.c:20:34
	movss	dword ptr [rsi + 4*rdx], xmm2
	.loc	1 21 47 is_stmt 1               # src/preprocess_core.c:21:47
	movzx	ecx, byte ptr [rdi - 2]
	.loc	1 21 40 is_stmt 0               # src/preprocess_core.c:21:40
	xorps	xmm1, xmm1
	cvtsi2ss	xmm1, ecx
	.loc	1 21 58                         # src/preprocess_core.c:21:58
	divss	xmm1, xmm0
	.loc	1 21 38                         # src/preprocess_core.c:21:38
	movss	dword ptr [rsi + 8*rdx], xmm1
	.loc	1 18 26 is_stmt 1               # src/preprocess_core.c:18:26
	add	rsi, 4
	add	rdi, 3
	add	rax, -1
	.loc	1 18 5 is_stmt 0                # src/preprocess_core.c:18:5
	jne	.LBB0_2
# %bb.3:
	.loc	1 0 5                           # src/preprocess_core.c:0:5
	pop	rbp
	.cfi_def_cfa rsp, 8
	.cfi_restore rbp
.LBB0_4:
	.loc	1 23 1 is_stmt 1                # src/preprocess_core.c:23:1
	ret
.Ltmp1:
.Lfunc_end0:
	.size	yolo_bgr8_to_rgb_chw_f32, .Lfunc_end0-yolo_bgr8_to_rgb_chw_f32
	.cfi_endproc
                                        # -- End function
	.section	.debug_abbrev,"",@progbits
	.byte	1                               # Abbreviation Code
	.byte	17                              # DW_TAG_compile_unit
	.byte	0                               # DW_CHILDREN_no
	.byte	37                              # DW_AT_producer
	.byte	14                              # DW_FORM_strp
	.byte	19                              # DW_AT_language
	.byte	5                               # DW_FORM_data2
	.byte	3                               # DW_AT_name
	.byte	14                              # DW_FORM_strp
	.byte	16                              # DW_AT_stmt_list
	.byte	23                              # DW_FORM_sec_offset
	.byte	27                              # DW_AT_comp_dir
	.byte	14                              # DW_FORM_strp
	.byte	17                              # DW_AT_low_pc
	.byte	1                               # DW_FORM_addr
	.byte	18                              # DW_AT_high_pc
	.byte	6                               # DW_FORM_data4
	.byte	0                               # EOM(1)
	.byte	0                               # EOM(2)
	.byte	0                               # EOM(3)
	.section	.debug_info,"",@progbits
.Lcu_begin0:
	.long	.Ldebug_info_end0-.Ldebug_info_start0 # Length of Unit
.Ldebug_info_start0:
	.short	4                               # DWARF version number
	.long	.debug_abbrev                   # Offset Into Abbrev. Section
	.byte	8                               # Address Size (in bytes)
	.byte	1                               # Abbrev [1] 0xb:0x1f DW_TAG_compile_unit
	.long	.Linfo_string0                  # DW_AT_producer
	.short	29                              # DW_AT_language
	.long	.Linfo_string1                  # DW_AT_name
	.long	.Lline_table_start0             # DW_AT_stmt_list
	.long	.Linfo_string2                  # DW_AT_comp_dir
	.quad	.Lfunc_begin0                   # DW_AT_low_pc
	.long	.Lfunc_end0-.Lfunc_begin0       # DW_AT_high_pc
.Ldebug_info_end0:
	.section	.debug_str,"MS",@progbits,1
.Linfo_string0:
	.byte	0                               # string offset=0
.Linfo_string1:
	.asciz	"src/preprocess_core.c"         # string offset=1
.Linfo_string2:
	.asciz	"."                             # string offset=23
	.section	".note.GNU-stack","",@progbits
	.addrsig
	.section	.debug_line,"",@progbits
.Lline_table_start0:
