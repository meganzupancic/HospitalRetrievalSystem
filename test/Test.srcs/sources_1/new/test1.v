`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 01/20/2025 08:41:51 PM
// Design Name: 
// Module Name: test1
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


module test1(
    input wire input1,
    input wire input2,
    output wire output1
    );
    
    wire wire1;
    
    Gate1Function gate1 (
        .a(input1),
        .b(input2),
        .out(wure1)
    );
    
    Gate2Function gate2 (
        .a(wire1),
        .b(input2),
        .out(output1)
    );

endmodule
