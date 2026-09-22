`default_nettype none
`timescale 1ns/1ps

module tb;

  reg clk = 0;
  reg rst_n = 0;
  reg ena = 1;
  reg [7:0] ui_in = 8'b0;
  reg [7:0] uio_in = 8'b0;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  tt_um_snake dut (
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

  // ~25.175MHz pixel clock -> ~39.7ns period, round to 40ns for sim
  always #20 clk = ~clk;

  integer frame_count;
  integer errors;

  initial begin
    $dumpfile("tb.vcd");
    $dumpvars(0, tb);

    errors = 0;
    frame_count = 0;

    // reset
    rst_n = 0;
    repeat (10) @(posedge clk);
    rst_n = 1;

    // hold RIGHT so the snake keeps moving predictably
    ui_in = 8'b0000_1000;

    // Run for a few vsync pulses and sanity-check sync polarity/timing
    repeat (2) begin
      @(negedge uo_out[3]); // vsync goes active (low)
      frame_count = frame_count + 1;
      $display("t=%0t : vsync asserted, frame %0d, game_over=%0d", $time, frame_count, uio_out[0]);
    end

    if (uio_oe !== 8'b0000_0001) begin
      $display("ERROR: uio_oe mismatch, got %b", uio_oe);
      errors = errors + 1;
    end

    if (errors == 0)
      $display("TB PASS: sync pulses observed, uio_oe correct.");
    else
      $display("TB FAIL: %0d error(s).", errors);

    $finish;
  end

  // Safety timeout (a couple of 640x480@60Hz frames is ~33.6ms of sim time
  // at a 40ns clock period)
  initial begin
    #60_000_000;
    $display("TB TIMEOUT");
    $finish;
  end

endmodule
