module ANDGate_tb; 
// Declare registers for the inputs and wire for the output 
reg a, b; 
wire out; 

// Instantiate the ANDGate module (DUT) 
ANDGate uut ( 
.a(a), 
.b(b), 
.out(out) 
); 

// Apply test cases 
initial begin 
// Apply test vectors and observe output 
a = 0; b = 0; #10;   // delays 10ns before execute next line
a = 0; b = 1; #10; 
a = 1; b = 0; #10; 
a = 1; b = 1; #10; 
end 
endmodule
