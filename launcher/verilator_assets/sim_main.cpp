#include "VMODULE_NAME.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    VMODULE_NAME* top = new VMODULE_NAME;

    VerilatedVcdC* tfp = new VerilatedVcdC;
    Verilated::traceEverOn(true);
    top->trace(tfp, 99);
    tfp->open("wave.vcd");

    for (int i = 0; i < 20; i++) {
        top->eval();
        tfp->dump(i * 10);
    }

    tfp->close();
    delete top;
    return 0;
}
