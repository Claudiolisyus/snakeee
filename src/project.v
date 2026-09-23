/*
 * TinyTapeout Snake
 * ------------------
 * A playable Snake game that drives a standard TinyVGA PMOD (640x480 @ 60Hz).
 *
 * Pinout
 *   ui_in[0] = UP
 *   ui_in[1] = DOWN
 *   ui_in[2] = LEFT
 *   ui_in[3] = RIGHT
 *   ui_in[4] = RESTART (also restarts after a game over)
 *   ui_in[7:5] = unused
 *
 *   uo_out[0] = R1      uo_out[4] = R0
 *   uo_out[1] = G1      uo_out[5] = G0
 *   uo_out[2] = B1      uo_out[6] = B0
 *   uo_out[3] = vsync   uo_out[7] = hsync
 *   (standard TinyVGA PMOD pin ordering)
 *
 *   uio_out[0] = game_over flag (1 = dead, waiting for restart), uio_oe[0]=1
 *   uio[7:1]   = unused, driven as inputs (oe = 0)
 *
 * Clock: expects ~25.175 MHz (the standard 640x480@60Hz pixel clock), e.g.
 * from the TinyTapeout PLL/clock generator or an external oscillator on a PMOD.
 *
 * The playfield is a 20x15 grid of 32x32 pixel cells (20*32=640, 15*32=480).
 * The snake's body is stored as a shift-register "history buffer": every
 * game tick every entry copies from its neighbour and the new head is
 * pushed in at index 0. Growing the snake is then simply a matter of
 * increasing `length` (the tail position is already sitting in history),
 * no extra data movement needed.
 */

`default_nettype none

module tt_um_snake #(
    parameter TICK_DIV = 22'd3_125_000 // 25_000_000 / 8 moves-per-second; override in sim for speed
) (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

  // ------------------------------------------------------------------
  // Grid geometry
  // ------------------------------------------------------------------
  localparam GRID_W   = 20;   // columns  (0 .. 19)
  localparam GRID_H   = 15;   // rows     (0 .. 14)
  localparam MAX_LEN  = 48;   // longest snake we bother storing history for

  // Directions
  localparam DIR_UP    = 2'd0;
  localparam DIR_DOWN  = 2'd1;
  localparam DIR_LEFT  = 2'd2;
  localparam DIR_RIGHT = 2'd3;

  // ------------------------------------------------------------------
  // VGA timing (640x480 @ 60Hz, ~25.175MHz pixel clock)
  // ------------------------------------------------------------------
  localparam H_VISIBLE = 640;
  localparam H_FRONT   = 16;
  localparam H_SYNC    = 96;
  localparam H_BACK    = 48;
  localparam H_TOTAL   = H_VISIBLE + H_FRONT + H_SYNC + H_BACK; // 800

  localparam V_VISIBLE = 480;
  localparam V_FRONT   = 10;
  localparam V_SYNC    = 2;
  localparam V_BACK    = 33;
  localparam V_TOTAL   = V_VISIBLE + V_FRONT + V_SYNC + V_BACK; // 525

  reg [9:0] hcount; // 0 .. 799
  reg [9:0] vcount; // 0 .. 524

  wire video_active = (hcount < H_VISIBLE) && (vcount < V_VISIBLE);
  wire hsync_n      = ~((hcount >= H_VISIBLE + H_FRONT) && (hcount < H_VISIBLE + H_FRONT + H_SYNC));
  wire vsync_n      = ~((vcount >= V_VISIBLE + V_FRONT) && (vcount < V_VISIBLE + V_FRONT + V_SYNC));

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      hcount <= 10'd0;
      vcount <= 10'd0;
    end else if (ena) begin
      if (hcount == H_TOTAL - 1) begin
        hcount <= 10'd0;
        if (vcount == V_TOTAL - 1)
          vcount <= 10'd0;
        else
          vcount <= vcount + 10'd1;
      end else begin
        hcount <= hcount + 10'd1;
      end
    end
  end

  // Current pixel's cell coordinates (cell = 32x32 px, so >>5)
  wire [4:0] pix_col = hcount[9:5]; // 0..24, only 0..19 valid in active video
  wire [3:0] pix_row = vcount[8:5]; // 0..16, only 0..14 valid in active video

  // ------------------------------------------------------------------
  // Game clock divider: turn ~25MHz into ~8 moves/second
  // ------------------------------------------------------------------
  reg [21:0] tick_cnt;
  wire       tick = (tick_cnt == TICK_DIV - 1);

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      tick_cnt <= 22'd0;
    else if (ena)
      tick_cnt <= tick ? 22'd0 : tick_cnt + 22'd1;
  end

  // ------------------------------------------------------------------
  // Direction latch (sampled continuously, applied on each game tick)
  // ------------------------------------------------------------------
  reg [1:0] dir;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dir <= DIR_RIGHT;
    end else if (ena) begin
      if (ui_in[0] && dir != DIR_DOWN)
        dir <= DIR_UP;
      else if (ui_in[1] && dir != DIR_UP)
        dir <= DIR_DOWN;
      else if (ui_in[2] && dir != DIR_RIGHT)
        dir <= DIR_LEFT;
      else if (ui_in[3] && dir != DIR_LEFT)
        dir <= DIR_RIGHT;
    end
  end

  // ------------------------------------------------------------------
  // Snake state
  // ------------------------------------------------------------------
  reg [8:0] body [0:MAX_LEN-1]; // {x[4:0], y[3:0]} per segment, body[0] = head
  reg [5:0] length;
  reg       game_over;

  reg [4:0] food_x;
  reg [3:0] food_y;

  // Free-running LFSR for pseudo-random food placement
  reg [15:0] lfsr;
  wire       lfsr_fb = lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10];

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      lfsr <= 16'hACE1;
    else if (ena)
      lfsr <= {lfsr[14:0], lfsr_fb};
  end

  // Candidate random coordinates, folded into range without a divider
  wire [4:0] rand_x_raw = lfsr[4:0];               // 0..31
  wire [4:0] rand_x     = (rand_x_raw >= GRID_W) ? (rand_x_raw - GRID_W) : rand_x_raw;
  wire [3:0] rand_y_raw = lfsr[8:5];                // 0..15
  wire [3:0] rand_y     = (rand_y_raw >= GRID_H) ? (rand_y_raw - GRID_H) : rand_y_raw;

  wire [4:0] head_x = body[0][8:4];
  wire [3:0] head_y = body[0][3:0];

  // Compute the candidate next head position based on current direction
  reg  [4:0] next_x;
  reg  [3:0] next_y;
  reg        wall_hit;

  always @(*) begin
    next_x   = head_x;
    next_y   = head_y;
    wall_hit = 1'b0;
    case (dir)
      DIR_UP: begin
        if (head_y == 4'd0) wall_hit = 1'b1;
        else                next_y   = head_y - 4'd1;
      end
      DIR_DOWN: begin
        if (head_y == GRID_H - 1) wall_hit = 1'b1;
        else                       next_y   = head_y + 4'd1;
      end
      DIR_LEFT: begin
        if (head_x == 5'd0) wall_hit = 1'b1;
        else                next_x   = head_x - 5'd1;
      end
      DIR_RIGHT: begin
        if (head_x == GRID_W - 1) wall_hit = 1'b1;
        else                       next_x   = head_x + 5'd1;
      end
    endcase
  end

  // Self-collision check against current body (before the shift happens)
  integer si;
  reg self_hit;
  always @(*) begin
    self_hit = 1'b0;
    for (si = 0; si < MAX_LEN; si = si + 1) begin
      if ((si < length) && (body[si][8:4] == next_x) && (body[si][3:0] == next_y))
        self_hit = 1'b1;
    end
  end

  wire eats_food = (next_x == food_x) && (next_y == food_y);

  integer gi;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      game_over <= 1'b0;
      length    <= 6'd3;
      food_x    <= 5'd15;
      food_y    <= 4'd7;
      for (gi = 0; gi < MAX_LEN; gi = gi + 1)
        body[gi] <= {5'd10 - gi[4:0], 4'd7}; // start heading right, tail trailing left
    end else if (ena) begin
      if (game_over) begin
        // Frozen until restart is pressed
        if (ui_in[4]) begin
          game_over <= 1'b0;
          length    <= 6'd3;
          food_x    <= rand_x;
          food_y    <= rand_y;
          for (gi = 0; gi < MAX_LEN; gi = gi + 1)
            body[gi] <= {5'd10 - gi[4:0], 4'd7};
        end
      end else if (tick) begin
        if (wall_hit || self_hit) begin
          game_over <= 1'b1;
        end else begin
          // shift history buffer, push new head at index 0
          for (gi = MAX_LEN - 1; gi > 0; gi = gi - 1)
            body[gi] <= body[gi-1];
          body[0] <= {next_x, next_y};

          if (eats_food) begin
            if (length < MAX_LEN)
              length <= length + 6'd1;
            food_x <= rand_x;
            food_y <= rand_y;
          end
        end
      end
    end
  end

  // ------------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------------
  reg is_body;
  integer ri;
  always @(*) begin
    is_body = 1'b0;
    for (ri = 0; ri < MAX_LEN; ri = ri + 1) begin
      if ((ri < length) && (body[ri][8:4] == pix_col) && (body[ri][3:0] == pix_row))
        is_body = 1'b1;
    end
  end

  wire is_head = (pix_col == head_x) && (pix_row == head_y);
  wire is_food = (pix_col == food_x) && (pix_row == food_y);

  // Position within the current 32x32 cell, used to draw food as a small
  // inset dot so it's still visually distinct from the snake in pure
  // black & white (no color channels to lean on anymore).
  wire [4:0] cell_px = hcount[4:0];
  wire [4:0] cell_py = vcount[4:0];
  wire       food_dot = is_food && (cell_px >= 5'd10) && (cell_px < 5'd22)
                                 && (cell_py >= 5'd10) && (cell_py < 5'd22);

  // 4-pixel border around the outer edges of the 640x480 screen
  wire is_border = (hcount < 10'd4) || (hcount >= (H_VISIBLE - 10'd4)) ||
                   (vcount < 10'd4) || (vcount >= (V_VISIBLE - 10'd4));

  reg pixel_white;
  always @(*) begin
    pixel_white = 1'b0;
    if (video_active) begin
      if (game_over) begin
        // Flashing black/white "you died" screen
        pixel_white = vcount[4];
      end else if (is_border) begin
        // Solid white border wall around playfield boundary
        pixel_white = 1'b1;
      end else if (is_head) begin
        // Blinking head so it reads distinctly from the solid body
        pixel_white = vcount[3];
      end else if (is_body) begin
        pixel_white = 1'b1;
      end else if (food_dot) begin
        pixel_white = 1'b1;
      end else begin
        pixel_white = 1'b0; // black background
      end
    end
  end

  assign uo_out[0] = pixel_white;
  assign uo_out[1] = pixel_white;
  assign uo_out[2] = pixel_white;
  assign uo_out[3] = vsync_n;
  assign uo_out[4] = pixel_white;
  assign uo_out[5] = pixel_white;
  assign uo_out[6] = pixel_white;
  assign uo_out[7] = hsync_n;

  assign uio_out    = {7'b0, game_over};
  assign uio_oe     = 8'b0000_0001;

  // Unused inputs
  wire _unused = &{ui_in[7:5], uio_in, ena, 1'b0};

endmodule
