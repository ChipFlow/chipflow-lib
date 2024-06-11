/* SPDX-License-Identifier: BSD-2-Clause */
#ifndef GPIO_H
#define GPIO_H

#include <stdint.h>

typedef struct __attribute__((packed, aligned(4))) {
	uint32_t out;
	uint32_t oe;
	uint32_t in;
} gpio_regs_t;

#endif
