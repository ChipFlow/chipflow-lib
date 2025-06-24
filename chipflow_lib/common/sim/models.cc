#undef NDEBUG

#include <cxxrtl/cxxrtl.h>
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <fstream>
#include <stdarg.h>
#include <unordered_map>
#include "models.h"

namespace cxxrtl_design {

// Helper functions

std::string vstringf(const char *fmt, va_list ap)
{
    std::string string;
    char *str = NULL;

#if defined(_WIN32) || defined(__CYGWIN__)
    int sz = 64 + strlen(fmt), rc;
    while (1) {
        va_list apc;
        va_copy(apc, ap);
        str = (char *)realloc(str, sz);
        rc = vsnprintf(str, sz, fmt, apc);
        va_end(apc);
        if (rc >= 0 && rc < sz)
            break;
        sz *= 2;
    }
#else
    if (vasprintf(&str, fmt, ap) < 0)
        str = NULL;
#endif

    if (str != NULL) {
        string = str;
        free(str);
    }

    return string;
}

std::string stringf(const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    std::string result = vstringf(format, ap);
    va_end(ap);
    return result;
}

// Action generation
namespace {
json input_cmds;
size_t input_ptr = 0;
std::unordered_map<std::string, std::vector<action>> queued_actions;

// Update the queued_actions map
void fetch_actions_into_queue() {
    while (input_ptr < input_cmds.size()) {
        auto &cmd = input_cmds.at(input_ptr);
        if (cmd["type"] == "wait")
            break;
        if (cmd["type"] != "action")
            throw std::out_of_range("invalid 'type' value for command");
        queued_actions[cmd["peripheral"]].emplace_back(cmd["event"], cmd["payload"]);
        ++input_ptr;
    }
}
}

void open_input_commands(const std::string &filename) {
    std::ifstream f(filename);
    if (!f) {
        throw std::runtime_error("failed to open event log for writing!");
    }
    json data = json::parse(f);
    input_cmds = data["commands"];
}

// Event logging

static std::ofstream event_log;

void open_event_log(const std::string &filename) {
    event_log.open(filename);
    if (!event_log) {
        throw std::runtime_error("failed to open event log for writing!");
    }
    event_log << "{" << std::endl;
    event_log << "\"events\": [" << std::endl;
    fetch_actions_into_queue();
}

void log_event(unsigned timestamp, const std::string &peripheral, const std::string &event_type, json payload) {
    static bool had_event = false;
    // Note: we don't use the JSON library to serialise the output event overall, so we get a partial log
    // even if the simulation crashes.
    // But we use `json` objects as a container for complex payloads that can be compared with the action input
    if (had_event)
        event_log << "," << std::endl;
    auto payload_str = payload.dump();
    event_log << stringf("{ \"timestamp\": %u, \"peripheral\": \"%s\", \"event\": \"%s\", \"payload\": %s }",
        timestamp, peripheral.c_str(), event_type.c_str(), payload_str.c_str());
    had_event = true;
    // Check if we have actions waiting on this
    if (input_ptr < input_cmds.size()) {
        const auto &cmd = input_cmds.at(input_ptr);
        // fetch_actions_into_queue should never leave input_ptr sitting on an action
        assert(cmd["type"] == "wait");
        if (cmd["peripheral"] == peripheral && cmd["event"] == event_type && cmd["payload"] == payload) {
            ++input_ptr;
            fetch_actions_into_queue();
        }
    }
}

std::vector<action> get_pending_actions(const std::string &peripheral) {
    std::vector<action> result;
    if (queued_actions.count(peripheral))
        std::swap(queued_actions.at(peripheral), result);
    return result;
}

void close_event_log() {
    event_log << std::endl << "]" << std::endl;
    event_log << "}" << std::endl;
    if (input_ptr != input_cmds.size()) {
        fprintf(stderr, "WARNING: not all input actions were executed (%d/%d remain)!\n",
             int(input_cmds.size()) - int(input_ptr), int(input_cmds.size()));
    }
}

// SPI flash
void spiflash_model::load_data(const std::string &filename, unsigned offset) {
    std::ifstream in(filename, std::ifstream::binary);
    if (offset >= data.size()) {
        throw std::out_of_range("flash: offset beyond end");
    }
    if (!in) {
        throw std::runtime_error("flash: failed to read input file: " + filename);
    }
    in.read(reinterpret_cast<char*>(data.data() + offset), (data.size() - offset));
}
void spiflash_model::step(unsigned timestamp) {
    auto process_byte = [&]() {
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
                throw std::runtime_error(stringf("flash: unknown command %02x", s.command));
            }
        } else {
            if (s.command == 0x03) {
                // Single read
                if (s.byte_count <= 3) {
                    s.addr |= (uint32_t(s.curr_byte) << ((3 - s.byte_count) * 8));
                }
                if (s.byte_count >= 3) {
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
    };

    if (csn && !s.last_csn) {
        s.bit_count = 0;
        s.byte_count = 0;
        s.data_width = 1;
    } else if (clk && !s.last_clk && !csn) {
        if (s.data_width == 4)
            s.curr_byte = (s.curr_byte << 4U) | (d_o.get<uint32_t>() & 0xF);
        else
            s.curr_byte = (s.curr_byte << 1U) | d_o.bit(0);
        s.out_buffer = s.out_buffer << unsigned(s.data_width);
        s.bit_count += s.data_width;
        if (s.bit_count == 8) {
            process_byte();
            ++s.byte_count;
            s.bit_count = 0;
        }
    } else if (!clk && s.last_clk && !csn) {
        if (s.data_width == 4) {
            d_i.set((s.out_buffer >> 4U) & 0xFU);
        } else {
            d_i.set(((s.out_buffer >> 7U) & 0x1U) << 1U);
        }
    }
    s.last_clk = bool(clk);
    s.last_csn = bool(csn);
}

// UART

void uart_model::step(unsigned timestamp) {

    for (auto action : get_pending_actions(name)) {
        if (action.event == "tx") {
            s.tx_active = true;
            s.tx_data = uint8_t(action.payload);
        }
    }

    if (s.rx_counter == 0) {
        if (s.tx_last && !tx) { // start bit
            s.rx_counter = 1;
        }
    } else {
        ++s.rx_counter;
        if (s.rx_counter > (baud_div / 2) && ((s.rx_counter - (baud_div / 2)) % baud_div) == 0) {
            int bit = ((s.rx_counter - (baud_div / 2)) / baud_div);
            if (bit >= 1 && bit <= 8) {
                // update shift register
                s.rx_sr = (tx ? 0x80U : 0x00U) | (s.rx_sr >> 1U);
            }
            if (bit == 8) {
                // print to console
                log_event(timestamp, name, "tx", json(s.rx_sr));
                if (name == "uart_0")
                    fprintf(stderr, "%c", char(s.rx_sr));
            }
            if (bit == 9) {
                // end
                s.rx_counter = 0;
            }
        }
    }
    s.tx_last = bool(tx);

    if (s.tx_active) {
        ++s.tx_counter;
        int bit = (s.tx_counter  / baud_div);
        if (bit == 0) {
            rx.set(0); // start
        } else if (bit >= 1 && bit <= 8) {
            rx.set((s.tx_data  >> (bit - 1)) & 0x1);
        } else if (bit == 9) { // stop
            rx.set(1);
        } else {
            s.tx_active = false;
        }
    } else {
        s.tx_counter = 0;
        rx.set(1); // idle
    }
}

// GPIO

void gpio_model::step(unsigned timestamp) {
    uint32_t o_value = o.get<uint32_t>();
    uint32_t oe_value = oe.get<uint32_t>();

    for (auto action : get_pending_actions(name)) {
        if (action.event == "set") {
            auto bin = std::string(action.payload);
            input_data = 0;
            for (unsigned i = 0; i < width; i++) {
                if (bin.at((width - 1) - i) == '1')
                    input_data |= (1U << i);
            }
        }
    }

    if (o_value != s.o_last || oe_value != s.oe_last) {
        std::string formatted_value;
        for (int i = width - 1; i >= 0; i--) {
            if (oe_value & (1U << unsigned(i)))
                formatted_value += (o_value & (1U << unsigned(i))) ? '1' : '0';
            else
                formatted_value += 'Z';
        }
        log_event(timestamp, name, "change", json(formatted_value));
    }

    i.set((input_data & ~oe_value) | (o_value & oe_value));
    s.o_last = o_value;
    s.oe_last = oe_value;
}

// Generic SPI model
void spi_model::step(unsigned timestamp) {
    for (auto action : get_pending_actions(name)) {
        if (action.event == "set_data") {
            s.out_buffer = s.send_data = uint32_t(action.payload);
        }
        if (action.event == "set_width") {
            s.width = uint32_t(action.payload);
        }
    }

    if (csn && !s.last_csn) {
        s.bit_count = 0;
        s.in_buffer = 0;
        s.out_buffer = s.send_data;
        log_event(timestamp, name, "deselect", json(""));
    } else if (!csn && s.last_csn) {
        log_event(timestamp, name, "select", json(""));
    } else if (clk && !s.last_clk && !csn) {
        s.in_buffer = (s.in_buffer << 1U) | copi.bit(0);
        s.out_buffer = s.out_buffer << 1U;
        s.bit_count += 1;
        if (s.bit_count == s.width) {
            log_event(timestamp, name, "data", json(s.in_buffer));
            s.bit_count = 0;
        }
    } else if (!clk && s.last_clk && !csn) {
        cipo.set(((s.out_buffer >> (s.width - 1U)) & 0x1U));
    }
    s.last_clk = bool(clk);
    s.last_csn = bool(csn);
}

// Generic I2C model
void i2c_model::step(unsigned timestamp) {
    bool sda = !bool(sda_oe), scl = !bool(scl_oe);

    for (auto action : get_pending_actions(name)) {
        if (action.event == "ack")
            s.do_ack = true;
        else if (action.event == "nack")
            s.do_ack = false;
        else if (action.event == "set_data")
            s.read_data = uint32_t(action.payload);
    }

    if (s.last_scl && s.last_sda && !sda) {
        // start
        log_event(timestamp, name, "start", json(""));
        s.sr = 0xFF;
        s.byte_count = 0;
        s.bit_count = 0;
        s.is_read = false;
        s.drive_sda = true;
    } else if (scl && !s.last_scl) {
        // SCL posedge
        if (s.byte_count == 0 || !s.is_read) {
            s.sr = (s.sr << 1) | (sda & 0x1);
        }
        s.bit_count += 1;
        if (s.bit_count == 8) {
            if (s.byte_count == 0) {
                // address
                s.is_read = (s.sr & 0x1);
                log_event(timestamp, name, "address", json(s.sr));
            } else if (!s.is_read) {
                log_event(timestamp, name, "write", json(s.sr));
            }
            s.byte_count += 1;
        } else if (s.bit_count == 9) {
            s.bit_count = 0;
        }
    } else if (!scl && s.last_scl) {
        // SCL negedge
        s.drive_sda = true; // idle high
        if (s.bit_count == 8) {
            s.drive_sda = !s.do_ack;
        } else if (s.byte_count > 0 && s.is_read) {
            if (s.bit_count == 0) {
                s.sr = s.read_data;
            } else {
                s.sr = s.sr << 1;
            }
            s.drive_sda = (s.sr >> 7) & 0x1;
        }
    } else if (s.last_scl && !s.last_sda && sda) {
        log_event(timestamp, name, "stop", json(""));
        s.drive_sda = true;
    }
 
    s.last_sda = sda;
    s.last_scl = scl;
    sda_i.set(sda && s.drive_sda);
    scl_i.set(scl);
}

}
