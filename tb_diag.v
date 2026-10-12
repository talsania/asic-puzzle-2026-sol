`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, I=0, enable=0;
wire [7:0] O; wire success;
puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));
always #5 clk = ~clk;
reg [120:0] cand [0:3-1];
integer i, t;
initial begin
  $readmemb("cands.txt", cand);
  for (i = 0; i < 3; i = i + 1) begin
    rst_n = 0; enable = 0; I = 0; repeat (3) @(negedge clk);
    rst_n = 1; @(negedge clk); enable = 1;
    for (t = 0; t < 121; t = t + 1) begin I = cand[i][120 - t]; @(negedge clk); end
    enable = 0; I = 0; repeat (1) @(negedge clk);
    $display("R %0d %b", i, {dut.n88, dut.n118, dut.n440, dut.n451, dut.n119, dut.n89, dut.n258, dut.n26, dut.n256, dut.n276, dut.n198, dut.n251, dut.n413, dut.n227, dut.n240, dut.n188, dut.n242, dut.n237, dut.n416, dut.n222, dut.n233, dut.n209, dut.n234, dut.n417, dut.n116, dut.n509, dut.n694, dut.n510, dut.n511, dut.n667, dut.n512, dut.n503, dut.n302, dut.n506, dut.n690, dut.n507, dut.n508, dut.n504, dut.n291, dut.n295, dut.n294, dut.n300, dut.n505, dut.n117, dut.n90, dut.n91, dut.n78, dut.n78});
  end
  $finish;
end
endmodule
