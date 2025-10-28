/* SPDX-License-Identifier: BSD-2-Clause */
#ifndef WB_MON_H
#define WB_MON_H

#include "build/sim/sim_soc.h"
#include <cxxrtl/cxxrtl.h>

namespace cxxrtl_design {

void wb_mon_set_output(bb_p_wb__mon &mon, const std::string &file);

}

#endif
