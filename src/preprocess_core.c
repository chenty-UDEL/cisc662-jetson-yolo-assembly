#include "preprocess_core.h"

/*
 * Mathematical reference for these operations in original benchmark.py:
 *   a = np.ascontiguousarray(a[:, :, ::-1].transpose(2, 0, 1))
 *   x = torch.from_numpy(a).to(device=device, dtype=dtype).unsqueeze(0) / 255.
 *
 * Input here is already letterboxed. This routine produces FP32 output on the
 * CPU. It excludes resizing/padding, transfer to CUDA, batching and inference.
 * The original benchmark performs these operations through NumPy/PyTorch;
 * this routine was not used to collect the reported Jetson timings.
 */
YOLO_EXPORT void yolo_bgr8_to_rgb_chw_f32(
    const unsigned char *restrict bgr,
    float *restrict rgb_chw,
    size_t pixel_count)
{
    for (size_t i = 0; i < pixel_count; ++i) {
        rgb_chw[i] = (float)bgr[3 * i + 2] / 255.0f;
        rgb_chw[pixel_count + i] = (float)bgr[3 * i + 1] / 255.0f;
        rgb_chw[2 * pixel_count + i] = (float)bgr[3 * i] / 255.0f;
    }
}
