#ifndef YOLO_PREPROCESS_CORE_H
#define YOLO_PREPROCESS_CORE_H

#include <stddef.h>

#if defined(_WIN32)
#define YOLO_EXPORT __declspec(dllexport)
#else
#define YOLO_EXPORT
#endif

/*
 * Reference operation AFTER LetterBox has produced an H x W BGR uint8 image.
 * bgr:     3 * pixel_count interleaved bytes, B G R B G R ...
 * rgb_chw: 3 * pixel_count floats, R plane, G plane, B plane, range [0, 1].
 * Buffers must not overlap and must be large enough; 3 * pixel_count must fit.
 * With pixel_count == 0 no memory is accessed, and null pointers are allowed.
 *
 * This is a new CPU C reference for the project's layout/normalization math.
 * It is not the original NumPy/PyTorch implementation or a YOLO GPU kernel.
 */
YOLO_EXPORT void yolo_bgr8_to_rgb_chw_f32(
    const unsigned char *restrict bgr,
    float *restrict rgb_chw,
    size_t pixel_count);

#endif
