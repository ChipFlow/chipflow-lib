/* SPDX-License-Identifier: BSD-2-Clause */
#ifndef SPIFLASH_H
#define SPIFLASH_H

#include "build/sim/sim_soc.h"
#include <cxxrtl/cxxrtl.h>

namespace cxxrtl_design {

void spiflash_load(bb_p_spiflash__model &flash, const std::string &file, size_t offset);

}

#endif
