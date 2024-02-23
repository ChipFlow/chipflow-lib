/* SPDX-License-Identifier: BSD-2-Clause */
#include "build/sim/sim_soc.h"
#include "log.h"
#include <cxxrtl/cxxrtl.h>
#include <fstream>
#include <stdexcept>
#include <array>

namespace cxxrtl_design {

struct spiflash_model : public bb_p_spiflash__model {
    struct {
        int bit_count = 0;
        int byte_count = 0;
        unsigned data_width = 1;
        uint32_t addr = 0;
        uint8_t curr_byte = 0;
        uint8_t command = 0;
        uint8_t out_buffer = 0;
    } s;

    std::vector<uint8_t> data;

    spiflash_model() {
        // TODO: don't hardcode
        data.resize(16*1024*1024);
        std::fill(data.begin(), data.end(), 0xFF); // flash starting value
    }

    void load(const std::string &file, size_t offset) {
        std::ifstream in(file, std::ifstream::binary);
        if (offset >= data.size()) {
            throw std::out_of_range("flash: offset beyond end");
        }
        if (!in) {
            throw std::runtime_error("flash: failed to read input file: " + file);
        }
        in.read(reinterpret_cast<char*>(data.data() + offset), (data.size() - offset));
    }

    void process_byte() {
        s.out_buffer = 0;
        if (s.byte_count == 0) {
            s.addr = 0;
            s.data_width = 1;
            s.command = s.curr_byte;
            if (s.command == 0xab) {
                // power up
            } else if (s.command == 0x03 || s.command == 0x9f || s.command == 0xff
                || s.command == 0x35 || s.command == 0x31 || s.command == 0x50
                || s.command == 0x05 || s.command == 0x01 || s.command == 0x06) {
                // nothing to do
            } else if (s.command == 0xeb) {
                s.data_width = 4;
            } else {
                log("flash: unknown command %02x\n", s.command);
            }
        } else {
            if (s.command == 0x03) {
                // Single read
                if (s.byte_count <= 3) {
                    s.addr |= (uint32_t(s.curr_byte) << ((3 - s.byte_count) * 8));
                }
                if (s.byte_count >= 3) {
                    //if (s.byte_count == 3)
                        //log("flash: begin read 0x%06x\n", s.addr);
                    s.out_buffer = data.at(s.addr);
                    s.addr = (s.addr + 1) & 0x00FFFFFF;
                }
            } else if (s.command == 0xeb) {
                // Quad read
                if (s.byte_count <= 3) {
                    s.addr |= (uint32_t(s.curr_byte) << ((3 - s.byte_count) * 8));
                }
                if (s.byte_count >= 6) { // 1 mode, 2 dummy clocks
                    // read 4 bytes
                    s.out_buffer = data.at(s.addr);
                    s.addr = (s.addr + 1) & 0x00FFFFFF;
                }
            }
        }
        if (s.command == 0x9f) {
            // Read ID
            static const std::array<uint8_t, 4> flash_id{0xCA, 0x7C, 0xA7, 0xFF};
            s.out_buffer = flash_id.at(s.byte_count % int(flash_id.size()));
        }
    }

    bool eval(performer *performer) override {
        if (posedge_p_csn__o()) {
            s.bit_count = 0;
            s.byte_count = 0;
            s.data_width = 1;
        } else if (posedge_p_clk__o() && !p_csn__o) {
            if (s.data_width == 4)
                s.curr_byte = (s.curr_byte << 4U) | (p_d__o.get<uint8_t>() & 0xF);
            else
                s.curr_byte = (s.curr_byte << 1U) | p_d__o.bit(0);
            s.out_buffer = s.out_buffer << unsigned(s.data_width);
            s.bit_count += s.data_width;
            if ((s.bit_count) == 8) {
                process_byte();
                ++s.byte_count;
                s.bit_count = 0;
            }
        } else if (negedge_p_clk__o() && !p_csn__o) {
            if (s.data_width == 4) {
                p_d__i.next.set<uint8_t>((s.out_buffer >> 4U) & 0xFU);
            } else {
                p_d__i.next.set<uint8_t>(((s.out_buffer >> 7U) & 0x1U) << 1U);
            }
        }
        return /*converged=*/true;
    }

    ~spiflash_model() {}
};

std::unique_ptr<bb_p_spiflash__model> bb_p_spiflash__model::create(std::string name, metadata_map parameters, metadata_map attributes) {
    return std::make_unique<spiflash_model>();
}

void spiflash_load(bb_p_spiflash__model &flash, const std::string &file, size_t offset) {
    dynamic_cast<spiflash_model&>(flash).load(file, offset);
}

}
