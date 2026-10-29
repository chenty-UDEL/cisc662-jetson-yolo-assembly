	.file	"preprocess_core.c"
	.text
	.globl	yolo_bgr8_to_rgb_chw_f32        // -- Begin function yolo_bgr8_to_rgb_chw_f32
	.p2align	2
	.type	yolo_bgr8_to_rgb_chw_f32,@function
yolo_bgr8_to_rgb_chw_f32:               // @yolo_bgr8_to_rgb_chw_f32
.Lfunc_begin0:
	.cfi_startproc
// %bb.0:
	.file	1 "." "src/preprocess_core.c"
	.loc	1 18 5 prologue_end             // src/preprocess_core.c:18:5
	cbz	x2, .LBB0_3
// %bb.1:
	.loc	1 0 5 is_stmt 0                 // src/preprocess_core.c:0:5
	mov	w10, #1132396544                // =0x437f0000
	lsl	x8, x2, #3
	.loc	1 18 5                          // src/preprocess_core.c:18:5
	add	x9, x0, #2
	fmov	s0, w10
	mov	x10, x2
.LBB0_2:                                // =>This Inner Loop Header: Depth=1
	.loc	1 19 22 is_stmt 1               // src/preprocess_core.c:19:22
	ldr	b1, [x9]
	.loc	1 20 36                         // src/preprocess_core.c:20:36
	ldur	b2, [x9, #-1]
	.loc	1 18 26                         // src/preprocess_core.c:18:26
	subs	x10, x10, #1
	.loc	1 21 40                         // src/preprocess_core.c:21:40
	ldur	b3, [x9, #-2]
	.loc	1 18 26                         // src/preprocess_core.c:18:26
	add	x9, x9, #3
	.loc	1 19 22                         // src/preprocess_core.c:19:22
	ucvtf	s1, s1
	.loc	1 20 36                         // src/preprocess_core.c:20:36
	ucvtf	s2, s2
	.loc	1 21 40                         // src/preprocess_core.c:21:40
	ucvtf	s3, s3
	.loc	1 19 44                         // src/preprocess_core.c:19:44
	fdiv	s1, s1, s0
	.loc	1 20 58                         // src/preprocess_core.c:20:58
	fdiv	s2, s2, s0
	.loc	1 19 20                         // src/preprocess_core.c:19:20
	str	s1, [x1]
	.loc	1 21 58                         // src/preprocess_core.c:21:58
	fdiv	s3, s3, s0
	.loc	1 20 34                         // src/preprocess_core.c:20:34
	str	s2, [x1, x2, lsl #2]
	.loc	1 21 38                         // src/preprocess_core.c:21:38
	str	s3, [x1, x8]
	.loc	1 18 26                         // src/preprocess_core.c:18:26
	add	x1, x1, #4
	.loc	1 18 5 is_stmt 0                // src/preprocess_core.c:18:5
	b.ne	.LBB0_2
.LBB0_3:
	.loc	1 23 1 is_stmt 1                // src/preprocess_core.c:23:1
	ret
.Ltmp0:
.Lfunc_end0:
	.size	yolo_bgr8_to_rgb_chw_f32, .Lfunc_end0-yolo_bgr8_to_rgb_chw_f32
	.cfi_endproc
                                        // -- End function
	.section	.debug_abbrev,"",@progbits
	.byte	1                               // Abbreviation Code
	.byte	17                              // DW_TAG_compile_unit
	.byte	0                               // DW_CHILDREN_no
	.byte	37                              // DW_AT_producer
	.byte	14                              // DW_FORM_strp
	.byte	19                              // DW_AT_language
	.byte	5                               // DW_FORM_data2
	.byte	3                               // DW_AT_name
	.byte	14                              // DW_FORM_strp
	.byte	16                              // DW_AT_stmt_list
	.byte	23                              // DW_FORM_sec_offset
	.byte	27                              // DW_AT_comp_dir
	.byte	14                              // DW_FORM_strp
	.byte	17                              // DW_AT_low_pc
	.byte	1                               // DW_FORM_addr
	.byte	18                              // DW_AT_high_pc
	.byte	6                               // DW_FORM_data4
	.byte	0                               // EOM(1)
	.byte	0                               // EOM(2)
	.byte	0                               // EOM(3)
	.section	.debug_info,"",@progbits
.Lcu_begin0:
	.word	.Ldebug_info_end0-.Ldebug_info_start0 // Length of Unit
.Ldebug_info_start0:
	.hword	4                               // DWARF version number
	.word	.debug_abbrev                   // Offset Into Abbrev. Section
	.byte	8                               // Address Size (in bytes)
	.byte	1                               // Abbrev [1] 0xb:0x1f DW_TAG_compile_unit
	.word	.Linfo_string0                  // DW_AT_producer
	.hword	29                              // DW_AT_language
	.word	.Linfo_string1                  // DW_AT_name
	.word	.Lline_table_start0             // DW_AT_stmt_list
	.word	.Linfo_string2                  // DW_AT_comp_dir
	.xword	.Lfunc_begin0                   // DW_AT_low_pc
	.word	.Lfunc_end0-.Lfunc_begin0       // DW_AT_high_pc
.Ldebug_info_end0:
	.section	.debug_str,"MS",@progbits,1
.Linfo_string0:
	.byte	0                               // string offset=0
.Linfo_string1:
	.asciz	"src/preprocess_core.c"         // string offset=1
.Linfo_string2:
	.asciz	"."                             // string offset=23
	.section	".note.GNU-stack","",@progbits
	.addrsig
	.section	.debug_line,"",@progbits
.Lline_table_start0:
