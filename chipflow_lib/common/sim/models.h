#ifndef MODELS_H
#define MODELS_H

#include <cxxrtl/cxxrtl.h>
#include <string>
#include <vector>
#include <algorithm>
#include <optional>

#include "vendor/nlohmann/json.hpp"


namespace cxxrtl_design {

using namespace cxxrtl;

using json = nlohmann::json;

std::string stringf(const char *format, ...);

struct action {
    action(const std::string &event, const json &payload) : event(event), payload(payload) {};
    std::string event;
    json payload;
};

void open_event_log(const std::string &filename);
void open_input_commands(const std::string &filename);
void log_event(unsigned timestamp, const std::string &peripheral, const std::string &event_type, json payload);
std::vector<action> get_pending_actions(const std::string &peripheral);
void close_event_log();

struct spiflash_model {
    std::string name;
    spiflash_model(const std::string &name, const value<1> &clk, const value<1> &csn, const value<4> &d_o, const value<4> &d_oe, value<4> &d_i) : 
        name(name), clk(clk), csn(csn), d_o(d_o), d_oe(d_oe), d_i(d_i) {
        data.resize(16*1024*1024);
        std::fill(data.begin(), data.end(), 0xFF); // flash starting value
    };

    void load_data(const std::string &filename, unsigned offset);
    void step(unsigned timestamp);

private:
    std::vector<uint8_t> data;
    const value<1> &clk;
    const value<1> &csn;
    const value<4> &d_o;
    const value<4> &d_oe;
    value<4> &d_i;
    // model state
    struct {
        bool last_clk = false, last_csn = false;
        int bit_count = 0;
        int byte_count = 0;
        unsigned data_width = 1;
        uint32_t addr = 0;
        uint8_t curr_byte = 0;
        uint8_t command = 0;
        uint8_t out_buffer = 0;
    } s;
};

struct uart_model {
    std::string name;
    uart_model(const std::string &name, const value<1> &tx, value<1> &rx, unsigned baud_div = 25000000/115200) : name(name), tx(tx), rx(rx), baud_div(baud_div) {};

    void step(unsigned timestamp);
private:
    const value<1> &tx;
    value<1> &rx;
    unsigned baud_div;

    // model state
    struct {
        bool tx_last;
        int rx_counter = 0;
        uint8_t rx_sr = 0;
        bool tx_active = false;
        int tx_counter = 0;
        uint8_t tx_data = 0;
    } s;
};

struct gpio_model {
    static constexpr unsigned width = 8;
    std::string name;
    gpio_model(const std::string &name, const value<width> &o, const value<width> &oe, value<width> &i) : name(name), o(o), oe(oe), i(i) {};

    void step(unsigned timestamp);

private:
    uint32_t input_data = 0;
    const value<width> &o;
    const value<width> &oe;
    value<width> &i;
    struct {
        uint32_t o_last = 0;
        uint32_t oe_last = 0;
    } s;
};


struct spi_model {
    std::string name;
    spi_model(const std::string &name, const value<1> &clk, const value<1> &csn, const value<1> &copi, value<1> &cipo) : 
        name(name), clk(clk), csn(csn), copi(copi), cipo(cipo) {
    };

    void step(unsigned timestamp);

private:
    std::vector<uint8_t> data;
    const value<1> &clk;
    const value<1> &csn;
    const value<1> &copi;
    value<1> &cipo;
    // model state
    struct {
        bool last_clk = false, last_csn = false;
        int bit_count = 0;
        uint32_t send_data = 0;
        uint32_t width = 8;
        uint32_t in_buffer = 0, out_buffer = 0;
    } s;
};

struct i2c_model {
    std::string name;
    i2c_model(const std::string &name, const value<1> &sda_oe, value<1> &sda_i, const value<1> &scl_oe, value<1> &scl_i) : name(name), sda_oe(sda_oe), sda_i(sda_i), scl_oe(scl_oe), scl_i(scl_i) {};

    void step(unsigned timestamp);
private:
    const value<1> &sda_oe;
    value<1> &sda_i;
    const value<1> &scl_oe;
    value<1> &scl_i;

    // model state
    struct {
        int byte_count = 0;
        int bit_count;
        bool do_ack;
        bool is_read;
        uint8_t read_data;
        uint8_t sr;
        bool drive_sda = true;
        bool last_sda, last_scl;
    } s;
};


}

#endif
