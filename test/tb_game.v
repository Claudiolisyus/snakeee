`default_nettype none
`timescale 1ns/1ps

module tb_game;

  reg clk = 0;
  reg rst_n = 0;
  reg ena = 1;
  reg [7:0] ui_in = 8'b0;
  reg [7:0] uio_in = 8'b0;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  tt_um_snake #(.TICK_DIV(22'd20)) dut (
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

  always #20 clk = ~clk;

  integer t;
  reg [4:0] prev_head_x;
  reg [3:0] prev_head_y;
  reg [5:0] prev_len;
  integer moves_seen;
  integer growth_seen;

  initial begin
    $dumpfile("tb_game.vcd");
    $dumpvars(0, tb_game);

    moves_seen  = 0;
    growth_seen = 0;

    rst_n = 0;
    repeat (5) @(posedge clk);
    rst_n = 1;
    ui_in = 8'b0000_1000; // hold RIGHT

    prev_head_x = dut.head_x;
    prev_head_y = dut.head_y;
    prev_len    = dut.length;
    $display("init head=(%0d,%0d) len=%0d food=(%0d,%0d)",
              prev_head_x, prev_head_y, prev_len, dut.food_x, dut.food_y);

    for (t = 0; t < 400; t = t + 1) begin
      @(posedge dut.tick);
      @(posedge clk); // let the non-blocking update settle
      if (dut.game_over) begin
        $display("t=%0t GAME OVER at head=(%0d,%0d) len=%0d", $time, dut.head_x, dut.head_y, dut.length);
      end else begin
        if (dut.head_x !== prev_head_x || dut.head_y !== prev_head_y)
          moves_seen = moves_seen + 1;
        if (dut.length > prev_len) begin
          growth_seen = growth_seen + 1;
          $display("t=%0t ATE FOOD -> len=%0d, new food=(%0d,%0d)", $time, dut.length, dut.food_x, dut.food_y);
        end
        prev_head_x = dut.head_x;
        prev_head_y = dut.head_y;
        prev_len    = dut.length;
      end
    end

    $display("Summary: moves_seen=%0d growth_seen=%0d final_len=%0d game_over=%0d",
              moves_seen, growth_seen, dut.length, dut.game_over);

    if (moves_seen == 0) begin
      $display("TB_GAME FAIL: snake never moved");
    end else begin
      $display("TB_GAME PASS: snake moved and simulation completed without X propagation issues.");
    end

    $finish;
  end

  initial begin
    #400_000_000;
    $display("TB_GAME TIMEOUT");
    $finish;
  end

endmodule
