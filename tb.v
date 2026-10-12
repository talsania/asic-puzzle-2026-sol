`timescale 1ns/1ps
module tb;
  reg clk=0, rst_n=0, I=0, enable=0;
  wire [7:0] O; wire success;
  puzzle dut(.clk(clk), .rst_n(rst_n), .I(I), .enable(enable), .O(O), .success(success));
  always #5 clk = ~clk;

  reg [8*256-1:0] bits;     // pass with +BITS=0110...
  integer i, n;
  initial begin
    if (!$value$plusargs("BITS=%s", bits)) bits = "0";
    n = 0; while (bits[8*n +: 8] != 0) n = n + 1;   // string length
    #12 rst_n = 1; enable = 1;
    for (i = n-1; i >= 0; i = i - 1) begin          // first char of string first
      I = (bits[8*i +: 8] == "1");
      @(posedge clk); #1;
      $display("t=%0d I=%b O=%b success=%b", n-1-i, I, O, success);
    end
    $finish;
  end
endmodule
