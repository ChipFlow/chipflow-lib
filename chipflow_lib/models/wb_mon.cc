/* SPDX-License-Identifier: BSD-2-Clause */
#include <cxxrtl/cxxrtl.h>
#include <fstream>
#include "build/sim/sim_soc.h"
#include "log.h"

namespace cxxrtl_design {

struct wb_mon : public bb_p_wb__mon {
    std::ofstream out;
    void set_output(const std::string &file) {
        out.open(file);
    }
    int stall_count = 0;
    bool eval(performer *performer) override {
        if (!out)
            return true;
        if (posedge_p_clk()) {
            if (p_stb && p_cyc && p_ack) { // TODO: pipelining
                uint32_t addr = (p_adr.get<uint32_t>() << 2U);
                uint32_t data = p_we ? p_dat__w.get<uint32_t>() : p_dat__r.get<uint32_t>();
                /*if (addr == 0xb1000000 && p_we)
                    log("debug: %x\n", (uint32_t)data);*/
                out << stringf("%08x,%c,", addr, p_we ? 'W' : 'R');

                for (int i = 3; i >= 0; i--) {
                    if (p_sel.bit(i))
                        out << stringf("%02x", (data >> (8 * i)) & 0xFF);
                    else
                        out << "__";
                }
                out << std::endl;
                stall_count = 0;
            } else if (p_stb && p_cyc) {
                ++stall_count;
                if (stall_count == 100000) {
                    stall_count = 0;
                    uint32_t addr = (p_adr.get<uint32_t>() << 2U);
                    out << stringf("%08x,%c,<STALL>", addr, p_we ? 'W' : 'R') << std::endl;
                }
            } else {
                stall_count = 0;
            }
        }
        return /*converged=true*/true;
    }

    void reset() override {
        bb_p_wb__mon::reset();
    }

    ~wb_mon() {}
};

std::unique_ptr<bb_p_wb__mon> bb_p_wb__mon::create(std::string name, metadata_map parameters, metadata_map attributes) {
    return std::make_unique<wb_mon>();
}

void wb_mon_set_output(bb_p_wb__mon &mon, const std::string &file) {
    dynamic_cast<wb_mon&>(mon).set_output(file);
}

}
