/* SPDX-License-Identifier: BSD-2-Clause */
#include "build/sim/sim_soc.h"
#include "log.h"
#include <cassert>
#include <cxxrtl/cxxrtl.h>
#include <fstream>
#include <stdexcept>

namespace cxxrtl_design {

struct hyperram_model : public bb_p_hyperram__model {
    struct {
        int dev = -1;
        unsigned clk_count = 0;
        uint32_t curr_cs = 0;
        uint64_t ca = 0;
        uint32_t addr = 0;
        uint16_t cfg0 = 0x8028;
        uint16_t latency = 7;
    } s;

    std::vector<uint8_t> data;
    int N; // number of devices

    hyperram_model() {
        assert(p_csn__o.bits <= 32);
        N = p_csn__o.bits;
        data.resize(N*8*1024*1024);
    }

    int decode_onecold(uint32_t cs) {
        int result = -1;
        for (int i = 0; i < N; i++) {
            if (((cs >> i) & 0x1) == 0x0) {
                if (result != -1)
                    log("multiple hyperram devices asserted! CS=%02x\n", cs);
                result = i;
            }
        }
        return result;
    }

    uint16_t lookup_latency(uint16_t cfg) {
        uint8_t lat_key = (cfg >> 4) & 0xF;
        switch (lat_key) {
            case 0b0000: return 5;
            case 0b0001: return 6;
            case 0b0010: return 7;
            case 0b1110: return 3;
            case 0b1111: return 4;
            default: log("unknown RAM latency %0x\n", lat_key); return 7;
        }
    }

    void handle_clk(bool posedge)
    {
        if (s.clk_count < 6) {
            p_rwds__i.next.set<bool>(true); // 2x latency; always
            s.ca |= uint64_t(p_dq__o.get<uint8_t>()) << ((5U - s.clk_count) * 8U);
        }
        if (s.clk_count == 6) {
            s.addr = ((((s.ca & 0x0FFFFFFFFFULL) >> 16U) << 3) | (s.ca & 0x7)) * 2; // *2 to convert word address to byte address
            s.addr += s.dev * (8U * 1024U * 1024U); // device offsets
        }
        if (s.clk_count >= 6) {
            bool is_reg = (s.ca >> 46) & 0x1;
            bool is_read = (s.ca >> 47) & 0x1;
            if (is_reg && !is_read && s.clk_count < 8) {
                s.cfg0 <<= 8;
                s.cfg0 |= p_dq__o.get<uint8_t>();
                if (s.clk_count == 7) {
                    s.latency = lookup_latency(s.cfg0);
                    // log("set latency %d\n", s.latency);
                }
            } else if (is_read && (s.clk_count >= (3 + 4 * s.latency))) {
                // log("read %08x %02x\n", s.addr, data.at(s.addr));
                p_dq__i.next.set<uint8_t>(data.at(s.addr++));
                p_rwds__i.next.set<bool>(posedge);
            } else if (!is_read && (s.clk_count >= (4 + 4 * s.latency))) {
                if (!p_rwds__o) { // data mask
                    // log("write %08x %02x\n", s.addr, p_dq__o.get<uint8_t>());
                    data.at(s.addr) = p_dq__o.get<uint8_t>();
                } else {
                    // log("write %08x XX\n", s.addr);
                }
                s.addr++;
            }
        }
        if (s.addr >= data.size())
            s.addr = 0;
        ++s.clk_count;
    }

    bool eval(performer *performer) override {
        uint32_t prev_cs = s.curr_cs;
        s.curr_cs = p_csn__o.get<uint32_t>();
        if (s.curr_cs != prev_cs) {
            // reset selected device
            s.dev = decode_onecold(s.curr_cs);
            // log("sel %d\n", s.dev);
            s.clk_count = 0;
            s.ca = 0;
        }
        if (posedge_p_clk__o() && s.dev != -1) {
            handle_clk(/*posedge=*/true);
        } else if (negedge_p_clk__o() && s.dev != -1) {
            handle_clk(/*posedge=*/false);
        }
        return /*converged=*/true;
    }

    ~hyperram_model() {}
}

std::unique_ptr<bb_p_hyperram__model> bb_p_hyperram__model::create(std::string name, metadata_map parameters, metadata_map attributes) {
    return std::make_unique<hyperram_model>();
}

}
