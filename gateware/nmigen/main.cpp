#include <iostream>
#include <fstream>

#include <backends/cxxrtl/cxxrtl_vcd.h>

#include TOP

using namespace std;

int main(int argc, char **argv)
{
    char *filename;
    int dump_level = 0;

    if (argc >= 3){
        filename = argv[1];
        dump_level = atoi(argv[2]);
    } 

    cxxrtl_design::p_top top;
    cxxrtl::debug_items all_debug_items;
    top.debug_info(all_debug_items);
    cxxrtl::vcd_writer vcd;
    std::ofstream waves;

    if (dump_level){
        vcd.timescale(1, "us");
        if (dump_level == 1)
            vcd.add(all_debug_items);
        else if (dump_level == 2)
            vcd.add_without_memories(all_debug_items);
        else if (dump_level == 3)
		    vcd.template add(all_debug_items, [](const std::string &, const debug_item &item) {
			    return item.type == debug_item::WIRE;
		    });
        waves.open(filename);
    }

    top.step();

    if (dump_level)
        vcd.sample(0);

    for(int j = 0; j < 20; ++j) {
        if(j == 1) top.p_rst = value<1>{1u};
        if(j == 10) top.p_rst = value<1>{0u};

        top.p_clk = value<1>{0u};
        top.step();

        if (dump_level)
            vcd.sample(j*2 + 0);

        top.p_clk = value<1>{1u};
        top.step();
        if (dump_level)
            vcd.sample(j*2 + 1);

        if (dump_level){
            waves << vcd.buffer;
            vcd.buffer.clear();
        }
    }

    for(int i=20;i<10000;++i){
        top.p_clk = value<1>{0u};
        top.step();

        if (dump_level)
            vcd.sample(i*2 + 0);

        top.p_clk = value<1>{1u};
        top.step();

        if (dump_level)
            vcd.sample(i*2 + 1);

        if (dump_level){
            waves << vcd.buffer;
            vcd.buffer.clear();
        }
    }
}