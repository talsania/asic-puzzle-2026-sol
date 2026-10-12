`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, I=0, enable=0;
wire [7:0] O; wire success;
puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));
always #5 clk = ~clk;
integer k, t;
task run(input integer kk);
begin
  rst_n=0; enable=0; I=0;
  repeat(3) @(negedge clk);
  rst_n=1; @(negedge clk);
  enable=1;
  for (t=0; t<121; t=t+1) begin I=(t==kk); @(negedge clk); end
  $display("%0d %b", kk, {dut.n170, dut.n241, dut.n173, dut.n243, dut.n175, dut.n183, dut.n194, dut.n252, dut.n29, dut.n24, dut.n200, dut.n228, dut.n202, dut.n210, dut.n205, dut.n231, dut.n207, dut.n220, dut.n211, dut.n245, dut.n259, dut.n274, dut.n265, dut.n282, dut.n267, dut.n292, dut.n286, dut.n285, dut.n12, dut.n16, dut.n646, dut.n697, dut.n649, dut.n676, dut.n651, dut.n689, dut.n655, dut.n680, dut.n658, dut.n665, dut.n660, dut.n684, dut.n693, dut.n699});
end
endtask
initial begin
  run(-1);
  for (k=0; k<121; k=k+1) run(k);
  $finish;
end
endmodule
