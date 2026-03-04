`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 01/20/2025 08:46:12 PM
// Design Name: 
// Module Name: test1_tb
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module test1_tb;
    reg input1, input2;
    wire output1;
    
    test1 uut(
        .input1(input1),
        .input2(input2),
        .output1(output1)
    );
    
    initial begin
        // Header for the output
        $display("input1 input2 | output1");
        $display("-----------------------");

        // Test case 1
        input1 = 0; input2 = 0; #10;
        $display("  %b      %b   |   %b", input1, input2, output1);

        // Test case 2
        input1 = 0; input2 = 1; #10;
        $display("  %b      %b   |   %b", input1, input2, output1);

        // Test case 3
        input1 = 1; input2 = 0; #10;
        $display("  %b      %b   |   %b", input1, input2, output1);

        // Test case 4
        input1 = 1; input2 = 1; #10;
        $display("  %b      %b   |   %b", input1, input2, output1);

        // End simulation
        $finish;
    end


endmodule
