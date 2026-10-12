`timescale 1ns/1ps
module tb;
reg clk=0, rst_n=0, I=0, enable=0;
wire [7:0] O; wire success;
puzzle dut(.clk(clk),.rst_n(rst_n),.I(I),.enable(enable),.O(O),.success(success));
always #5 clk = ~clk;
reg [120:0] cand [0:1-1];
integer i, t, c;
initial begin
  $readmemb("cands.txt", cand);
  for (i = 0; i < 1; i = i + 1) begin
    rst_n = 0; enable = 0; I = 0; repeat (3) @(negedge clk);
    rst_n = 1; @(negedge clk); enable = 1;
    for (t = 0; t < 121; t = t + 1) begin I = cand[i][120 - t]; @(negedge clk); end
    enable = 0; I = 0;
    for (c = 0; c < 4000; c = c + 1) begin @(negedge clk); $display("R %0d %0d %b %h", i, c, success, O); end
  end
  $finish;
end
endmodule
