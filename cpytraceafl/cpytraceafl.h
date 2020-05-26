#include <stdint.h>
#include <string.h>

extern unsigned char afl_map_size_bits;
extern unsigned char afl_ngram_size;

#define NGRAM_SIZE_MAX 16U
#define PREV_LOC_SIZE_MAX sizeof(uint64_t)
#define PREV_LOC_VECTOR_SIZE_MAX NGRAM_SIZE_MAX*PREV_LOC_SIZE_MAX

// we over-allocate as much prev_loc space as we could possibly need
// (given the above values) because at compile-time we don't know what
// ngram settings (if any) will be in use
typedef struct {
    union {
        char byte[PREV_LOC_VECTOR_SIZE_MAX];
        uint32_t u32[NGRAM_SIZE_MAX];
    } as;
} afl_prev_loc_vector_t;

extern __thread afl_prev_loc_vector_t __afl_prev_loc;
extern char* __afl_area_ptr;

// the least significant afl_map_size_bits bits will be used to generate the final
// map location, so callers should ensure that's where the most entropy is packed
static inline void cpytraceafl_record_loc(uint32_t this_loc) {
    uint32_t prev_loc = __afl_prev_loc.as.u32[0];
    if (afl_ngram_size) {
        // reduce ngram elements into prev_loc
        for (int i=1; i < afl_ngram_size; i++) {
            prev_loc ^= __afl_prev_loc.as.u32[i];
        }
    }

    uint32_t map_slot = this_loc ^ prev_loc;
    // ensure we can't be addressing outside our allocated region for whatever reason
    map_slot &= (~(uint32_t)0) >> (32-afl_map_size_bits);
    // mimic "never zero" behaviour when incrementing visits
    uint8_t visits = __afl_area_ptr[map_slot] + 1;
    __afl_area_ptr[map_slot] = visits ? visits : 1;

    if (afl_ngram_size) {
        // advance the conveyor belt
        memmove(&__afl_prev_loc.as.u32[1], __afl_prev_loc.as.u32, sizeof(uint32_t) * (afl_ngram_size-1));
    }
    __afl_prev_loc.as.u32[0] = this_loc>>1;
}
