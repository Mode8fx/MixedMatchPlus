; MixedMatchPlus native 65816 extensions. A=8-bit, X/Y=16-bit unless stated.
; $1EF0: 0=one player, 1=two players; $1EF1/$1EF2: added menu cursors.
; Existing menus/settings, game stages, timers, and rules remain the game engine's.

org $8AEA00
normal_init:
  inc.w $0305
  stz.w $1EF1
  stz.w $1EF0
  lda.b #$01
  rtl
custom_init:
  inc.w $0305
  stz.w $1EF2
  stz.w $1EF0
  lda.b #$00
  rtl

normal_initial_maps:
  jsr.w $E721
  ; The normal menu uses pixel-shifted choices and setting headers.
  ; Load with the native maps while the screen is forced blank, before fade-in.
  lda.b #$9D
  pha
  pea.w $8000
  pea.w $3800
normal_font_length:
  pea.w $0000 ; Filled by the build with the generated graphics length.
  jsl.l $808B0B
  ; Palette 4 has the native white lettering plus animated focus-border colors.
  rep.b #$20
  ldx.w #$001E
normal_focus_palette_copy:
  lda.w $1500,X
  sta.w $1580,X
  dex
  dex
  bpl normal_focus_palette_copy
  sep.b #$20
  rts

normal_input:
  phk
  plb
  rep.b #$20
  lda.b $41
  bit.w #$1000
  sep.b #$20
  beq normal_not_start
  jsr.w $E4DC
  rts
normal_not_start:
  rep.b #$20
  lda.b $41
  bit.w #$8000
  sep.b #$20
  beq normal_not_back
  jsr.w $E4D0
  rts
normal_not_back:
  rep.b #$20
  lda.b $41
  bit.w #$0800
  sep.b #$20
  beq normal_not_up
  lda.w $1EF1
  beq normal_not_up
  jsr.w $E433
  dec.w $1EF1
normal_not_up:
  rep.b #$20
  lda.b $41
  bit.w #$0400
  sep.b #$20
  beq normal_not_down
  lda.w $1EF1
  cmp.b #$03
  beq normal_not_down
  jsr.w $E433
  inc.w $1EF1
normal_not_down:
  lda.w $1EF1
  dec A
  sta.w $0C08
  rep.b #$20
  lda.b $41
  bit.w #$0300
  sep.b #$20
  beq normal_p2
  lda.w $1EF1
  bne normal_setting
  lda.b $42
  and.b #$01
  sta.w $1EF0
  bra normal_p2
normal_setting:
  lda.b $42
  and.b #$02
  beq normal_right
  jsr.w $E502
  bra normal_p2
normal_right:
  jsr.w $E54A
normal_p2:
  lda.w $1EF0
  beq normal_input_done
  jsr.w $E592
normal_input_done:
  rts

normal_draw:
  jsl.l draw_normal_count
  rts

custom_input:
  phk
  plb
  rep.b #$20
  lda.b $41
  bit.w #$1000
  sep.b #$20
  beq custom_not_start
  jsr.w $DFE2
  rts
custom_not_start:
  rep.b #$20
  lda.b $41
  bit.w #$8000
  sep.b #$20
  beq custom_not_back
  jsr.w $DFD6
  rts
custom_not_back:
  rep.b #$20
  lda.b $41
  bit.w #$0800
  sep.b #$20
  beq custom_not_up
  lda.w $1EF2
  beq custom_not_up
  jsr.w $E433
  dec.w $1EF2
custom_not_up:
  rep.b #$20
  lda.b $41
  bit.w #$0400
  sep.b #$20
  beq custom_not_down
  lda.w $1EF2
  cmp.b #$08
  beq custom_not_down
  jsr.w $E433
  inc.w $1EF2
custom_not_down:
  lda.w $1EF2
  cmp.b #$07
  bcc custom_cursor_mapped
  beq custom_music_cursor
  lda.b #$07
  bra custom_cursor_mapped
custom_music_cursor:
  lda.b #$00
custom_cursor_mapped:
  dec A
  sta.w $0C08
  rep.b #$20
  lda.b $41
  bit.w #$0300
  sep.b #$20
  beq custom_p2
  lda.w $1EF2
  bne custom_setting
  lda.b $42
  and.b #$01
  sta.w $1EF0
  bra custom_p2
custom_setting:
  cmp.b #$07
  beq custom_music_input
  lda.b $42
  and.b #$02
  beq custom_right
  jsr.w $E010
  bra custom_p2
custom_right:
  jsr.w $E02A
  bra custom_p2
custom_music_input:
  lda.b $42
  and.b #$02
  beq custom_music_right
  lda.w $1EA9
  dec A
  bra custom_music_store
custom_music_right:
  lda.w $1EA9
  inc A
custom_music_store:
  and.b #$03
  sta.w $1EA9
  jsr.w $E42C
  jsl.l $80827B
custom_p2:
  lda.w $1EF0
  beq custom_input_done
  jsr.w $E044
custom_input_done:
  rts

custom_draw:
  jsr.w $E2E2
  jsl.l draw_custom_count
  rts

; Player two has no input processing, board update, or stage transition in solo.
mixed_second:
  lda.w $1EF0
  beq mixed_second_done
  ldx.w #$0500
  stx.w $0B00
  jsr.w $CFDC
  jsr.w $D2AD
  jsr.w $D6A8
mixed_second_done:
  rts
mixed_input_two:
  lda.w $1EF0
  beq mixed_input_none
  ldy.b $39
  sty.w $0774
  ldy.b $43
  sty.w $0776
  rts
mixed_input_none:
  ldy.w #$0000
  sty.w $0774
  sty.w $0776
  rts
mixed_controls_two:
  lda.w $1EF0
  beq mixed_controls_done
  ldx.w #$0500
  stx.w $0B00
  jsr.w $8457
mixed_controls_done:
  rts
mixed_init_two:
  stz.w $1EF4
  lda.w $1EF0
  beq mixed_clear_two
  ldx.w #$0500
  stx.w $0B00
  jsr.w $ADBA
  rts
mixed_clear_two:
  rep.b #$20
  ldx.w #$0000
  lda.w #$0000
mixed_clear_two_loop:
  sta.w $0600,X
  inx
  inx
  cpx.w #$0400
  bne mixed_clear_two_loop
  sep.b #$20
  rts
mixed_finish:
  jsl.l timer_prepare
  lda.w $1EF0
  bne mixed_two_finish
  lda.w $03F2
  beq mixed_finish_done
  jmp.w $D797
mixed_two_finish:
  jmp.w $D78D
mixed_finish_done:
  rts

mixed_pause:
  lda.w $1EF0
  bne original_pause
  lda.w $0B1B
  bne original_pause
  lda.w $0407
  beq solo_pause_done
  lda.w $0C78
  beq solo_pause_ready
  dec.w $0C78
  rts
solo_pause_ready:
  rep.b #$20
  lda.w $0276
  bit.w #$1000
  sep.b #$20
  beq solo_pause_done
  lda.b #$1E
  sta.w $0C78
  ldx.w #$0000
  stx.w $0B00
  lda.w $0304
  bne solo_unpause
  phk
  plb
  tdc
  lda.w $0305
  tay
  lda.w $D65A,Y
  bne solo_pause_done
  lda.b #$40
  sta.w $0304
  lda.b #$08
  sta.b $00
  jsr.w $D25C
  jsl.l $809259
  lda.b #$07
  jsl.l $8092C3
  jsr.w $D5D9
  bra solo_pause_done
solo_unpause:
  stz.w $0304
  lda.b #$09
  sta.b $00
  jsr.w $D25C
  jsl.l $809259
  lda.b #$07
  jsl.l $8092C3
  jsr.w $D647
solo_pause_done:
  rts
original_pause:
  jmp.w $D55B

mixed_timer_two:
  lda.w $1EF0
  beq solo_timer_done
  ldx.w #$0500
  stx.w $0B00
  jmp.w $D73B
solo_timer_done:
  rts

solo_results:
  lda.w $1EF0
  beq solo_results_main
  jsr.w $D8F8
  jsl.l $80942C
  rtl
solo_results_main:
  phk
  plb
  stz.b $4D
  stz.b $4E
  lda.w $0305
  cmp.b #$01
  beq solo_results_sound
  cmp.b #$02
  beq solo_results_fade
  cmp.b #$03
  beq solo_results_build
  cmp.b #$04
  beq solo_results_input
  ; Same fade back to Mixed Match title as the original results screen.
  jsr.w $DADD
  bra solo_results_draw
solo_results_sound:
  jsr.w $D916
  bra solo_results_draw
solo_results_fade:
  jsr.w $D921
  bra solo_results_draw
solo_results_build:
  jsl.l solo_results_template
  ldx.w #$0000
  stx.w $0B00
  jsr.w $DC1F
  jsr.w $DC55
  jsr.w $DC92
  jsr.w $DD2D
  jsr.w $DCF7
  jsl.l solo_results_scores
  lda.b #$04
  sta.w $0305
  bra solo_results_draw
solo_results_input:
  rep.b #$20
  lda.b $41
  bit.w #$1080
  sep.b #$20
  beq solo_results_draw
  inc.w $0305
solo_results_draw:
  jsl.l $80942C
  rtl

; The stock load already runs with the screen blank. Replace the decorative
; layers with full-width solo maps after its normal field/graphics setup.
solo_initial_maps:
  jsr.w $D213
  jsl.l timer_load
  lda.w $1EF0
  bne solo_initial_maps_done
  ; The shared foreground tile $2C8 is the two-player checkerboard divider.
  ; Upload the native transparent tile over it in solo only. All phases share
  ; this graphics set; their later map reloads cannot bring the divider back.
  lda.b #$8E
  pha
  pea.w $8000
  pea.w $3C80
  pea.w $0020
  jsl.l $808B0B
  ; The LINE/LEVEL/HEIGHT frame junctions have checker pixels baked in too.
  ; Use solo copies with that strip erased, keeping their beveled borders.
  lda.b #$9C
  pha
  pea.w $B000
  pea.w $3360
  pea.w $0140
  jsl.l $808B0B
  ; LEVEL and HEIGHT end in text tiles that also contain the divider strip.
  lda.b #$9C
  pha
  pea.w $B140
  pea.w $2A50
  pea.w $0020
  jsl.l $808B0B
  lda.b #$9C
  pha
  pea.w $B160
  pea.w $2B50
  pea.w $0020
  jsl.l $808B0B
  lda.b #$9C
  pha
  pea.w $C000
  pea.w $0400
  pea.w $0800
  jsl.l $808B0B
  lda.b #$9C
  pha
  pea.w $C800
  pea.w $0800
  pea.w $0800
  jsl.l $808B0B
solo_initial_maps_done:
  rts

; Reuse the original transition DMA schedule: one row per frame. Only the
; decorative BG2/BG3 transfers grow from 16 to 32 tiles; BG1 stays a single field.
solo_reload_init:
  jsr.w $D37F
  lda.w $1EF0
  bne solo_reload_done
  lda.b #$40
  sta.b $B7
  sta.b $C1
  lda.b #$9C
  sta.b $B6
  sta.b $C0
  lda.w $03F1
  cmp.b #$03
  beq solo_reload_dr
  cmp.b #$05
  beq solo_reload_final
  ldx.w #$C000
  ldy.w #$C800
  bra solo_reload_sources
solo_reload_dr:
  ldx.w #$D000
  ldy.w #$D800
  bra solo_reload_sources
solo_reload_final:
  ldx.w #$E000
  ldy.w #$E800
solo_reload_sources:
  stx.b $B4
  sty.b $BE
solo_reload_done:
  rts

org $83EF00
mixed_sprites:
  ldx.w #$0000
  stx.w $0B00
  jsr.w $DD54
  lda.w $1EF0
  beq mixed_sprites_done
  ldx.w #$0500
  stx.w $0B00
  jsr.w $DD54
mixed_sprites_done:
  rtl
normal_second_marker:
  lda.w $1EF0
  beq normal_count_marker
  jsr.w $DF82
normal_count_marker:
  ; Same green arrow frame as PLAY TIME, placed before the selected numeral.
  lda.w $1EF0
  asl A
  asl A
  asl A
  asl A
  clc
  adc.b #$30
  sta.b $02
  lda.b #$39
  sta.b $04
  lda.b #$32
  sta.w $1DC9
  lda.b #$0F
  jmp.w $DB62

org $80D000
solo_display:
  php
  rep.b #$30
  pha
  phx
  phy
  phb
  sep.b #$20
  lda.w $0BAF
  cmp.b #$30
  bne solo_display_done
  lda.w $1EF0
  bne solo_display_done
  lda.b #$50
  ldx.w $03F1
  cpx.w #$0003
  bne solo_shift_ready
  lda.b #$48
solo_shift_ready:
  sta.w $1EF3
  rep.b #$20
  and.w #$00FF
  eor.w #$FFFF
  inc A
  sta.b $4F
  sta.b $53
  sta.b $57
  sep.b #$20
  ; Keep the foreground and sprites in the solo pane. The extended decorative
  ; BG2/BG3 layers remain visible across the entire screen.
  lda.b #$03
  sta.w $2123
  sta.w $2125
  stz.w $2124
  lda.b #$11
  sta.b $4D
  sta.b $4E
  ldx.w #$1900
solo_sprite_loop:
  cpx.w $1DC5
  bcs solo_display_done
  lda.b $00,X
  clc
  adc.w $1EF3
  sta.b $00,X
  inx
  inx
  inx
  inx
  bra solo_sprite_loop
solo_display_done:
  plb
  rep.b #$30
  ply
  plx
  pla
  plp
  jsr.w $8B34
  rts

solo_windows:
  lda.w $0BAF
  cmp.b #$30
  bne original_windows
  lda.w $1EF0
  bne original_windows
  ; Offset the engine's logical wipe window without modifying its counters.
  lda.b $6C
  clc
  adc.w $1EF3
  sta.w $2126
  lda.b $6D
  clc
  adc.w $1EF3
  sta.w $2127
  lda.b $6E
  sta.w $2128
  lda.b $6F
  sta.w $2129
  rts
original_windows:
  jmp.w $8D47

; Run after the native queued VRAM transfers and palette DMA, before display
; enable. Only 48 bytes are transferred; tile selection and foreground clearing
; happen in game logic. BG2 lies outside the solo BG1/OBJ clipping window.
org $80D100
mixed_timer_display:
  jsr.w $8B57
  php
  rep.b #$30
  pha
  phx
  phy
  sep.b #$20
  lda.w $0BAF
  cmp.b #$30
  bne mixed_timer_display_done
  lda.w $1EF4
  beq mixed_timer_display_done
  jsl.l timer_transfer
mixed_timer_display_done:
  rep.b #$30
  ply
  plx
  pla
  plp
  rts

org $9C8500
timer_load:
  lda.b #$9D
  pha
  pea.w $9000
  pea.w $4000
timer_font_length:
  pea.w $0000
  jsl.l $808B0B
  ; A transparent BG3 tile for the panel's subscreen cutout. Otherwise native
  ; background subtraction tints the white digits green/pink/gold.
  lda.b #$8E
  pha
  pea.w $8000
  pea.w $5FF8
  pea.w $0010
  jsl.l $808B0B
  jsl.l timer_prepare
  lda.b #$01
  sta.w $1EF4
  rtl

; Prepare pixels/map words during game logic. Vblank only performs four short
; DMA transfers, preserving the native graphics and palette transfer budget.
timer_prepare:
  php
  rep.b #$30
  phx
  phy
  lda.b $00
  pha
  lda.b $02
  pha
  lda.b $04
  pha
  lda.w $1EF0
  and.w #$00FF
  bne timer_two_position
  ; Panel top-left: solo (184,184), two players (104,184). BG2 scroll
  ; shifts Tetris by 80px and Dr. Mario by 72px, so solo uses columns 13/14.
  lda.w #$06ED
  ldx.w $03F1
  cpx.w #$0003
  bne timer_position_ready
  inc A
  bra timer_position_ready
timer_two_position:
  lda.w #$06ED
timer_position_ready:
  sta.b $00
  sta.w $1EFA
  ; Clear the foreground locally before its existing full-map DMA. In solo
  ; this is outside the clipped field; in two-player it removes the divider.
  sec
  sbc.w #$0400
  asl A
  tax
  ldy.w #$0004
timer_clear_foreground_row:
  lda.w #$0000
  sta.l $7F0000,X
  sta.l $7F0002,X
  sta.l $7F0004,X
  sta.l $7F0006,X
  sta.l $7F0008,X
  sta.l $7F000A,X
  txa
  clc
  adc.w #$0040
  tax
  dey
  bne timer_clear_foreground_row
  ; Binary engine clock: minutes 0..30, seconds 0..59. Clamp a transient
  ; underflow rather than indexing beyond the tables during timer expiry.
  lda.w $040A
  and.w #$00FF
  cmp.w #$001F
  bcc timer_minutes_valid
  lda.w #$0000
timer_minutes_valid:
  sta.b $02
  asl A
  clc
  adc.b $02
  asl A
  asl A
  sta.b $02
  lda.w $0409
  and.w #$00FF
  cmp.w #$003C
  bcc timer_seconds_valid
  lda.w #$0000
timer_seconds_valid:
  sta.b $04
  asl A
  clc
  adc.b $04
  asl A
  asl A
  sta.b $04
  ldx.w #$0000
timer_frame_buffer:
  lda.l $9C9300,X
  sta.l $7F0D00,X
  lda.l $9C930C,X
  sta.l $7F0D24,X
  inx
  inx
  cpx.w #$000C
  bne timer_frame_buffer
  ldx.b $02
  lda.l $9C9400,X
  sta.l $7F0D0C
  lda.l $9C9402,X
  sta.l $7F0D0E
  lda.l $9C9404,X
  sta.l $7F0D10
  lda.l $9C9406,X
  sta.l $7F0D18
  lda.l $9C9408,X
  sta.l $7F0D1A
  lda.l $9C940A,X
  sta.l $7F0D1C
  ldx.b $04
  lda.l $9CA000,X
  sta.l $7F0D12
  lda.l $9CA002,X
  sta.l $7F0D14
  lda.l $9CA004,X
  sta.l $7F0D16
  lda.l $9CA006,X
  sta.l $7F0D1E
  lda.l $9CA008,X
  sta.l $7F0D20
  lda.l $9CA00A,X
  sta.l $7F0D22
  pla
  sta.b $04
  pla
  sta.b $02
  pla
  sta.b $00
  ply
  plx
  plp
  rtl

timer_transfer:
  ; Palette/transition frames sometimes consume the end of vblank. Retain the
  ; previous timer image on those frames rather than writing VRAM during play.
  ; The next available frame uses the current native clock, with no lost ticks.
  lda.b $32
  bmi timer_transfer_ready
  lda.w $4212
  bpl timer_transfer_done
  lda.w $213F
  lda.w $2137
  lda.w $213D
  pha
  lda.w $213D
  and.b #$01
  beq timer_transfer_low_line
  pla
  cmp.b #$03
  bcs timer_transfer_done
  bra timer_transfer_ready
timer_transfer_low_line:
  pla
timer_transfer_ready:
  lda.b #$80
  sta.w $2115
  ldx.w #$1801
  stx.w $4300
  ldx.w #$0D00
  stx.w $4302
  lda.b #$7F
  sta.w $4304
  ldx.w $1EFA
  ldy.w #$000C
  stx.w $2116
  sty.w $4305
  lda.b #$01
  sta.w $420B
  rep.b #$20
  txa
  clc
  adc.w #$0020
  tax
  sep.b #$20
  stx.w $2116
  sty.w $4305
  lda.b #$01
  sta.w $420B
  rep.b #$20
  txa
  clc
  adc.w #$0020
  tax
  sep.b #$20
  stx.w $2116
  sty.w $4305
  lda.b #$01
  sta.w $420B
  rep.b #$20
  txa
  clc
  adc.w #$0020
  tax
  sep.b #$20
  stx.w $2116
  sty.w $4305
  lda.b #$01
  sta.w $420B
timer_transfer_done:
  rtl

org $9C8000
draw_normal_count:
  php
  phx
  sep.b #$20
  lda.w $1EF1
  beq normal_count_focused
  lda.b #$00
  bra normal_count_palette
normal_count_focused:
  lda.b #$08
normal_count_palette:
  sta.b $00
  ldx.w #$0000
draw_normal_count_loop:
  lda.l $7F0109,X
  and.b #$E3
  ora.b $00
  sta.l $7F0109,X
  lda.l $7F0189,X
  and.b #$E3
  ora.b $00
  sta.l $7F0189,X
  inx
  inx
  cpx.w #$0012
  bne draw_normal_count_loop
  lda.l $7F0149
  and.b #$E3
  ora.b $00
  sta.l $7F0149
  lda.l $7F0159
  and.b #$E3
  ora.b $00
  sta.l $7F0159
  jsl.l draw_normal_frames
  plx
  plp
  rtl

draw_custom_count:
  php
  rep.b #$20
  phx
  phy
  ldx.w #$0000
draw_custom_count_loop:
  lda.l $9C9040,X
  sta.l $7F0112,X
  inx
  inx
  cpx.w #$001A
  bne draw_custom_count_loop
  sep.b #$20
  lda.w $1EF0
  inc A
  sta.l $7F0112
  lda.w $1EF2
  bne custom_count_draw_done
  ldx.w #$0000
custom_count_highlight:
  lda.l $7F0113,X
  ora.b #$04
  sta.l $7F0113,X
  inx
  inx
  cpx.w #$001A
  bne custom_count_highlight
custom_count_draw_done:
  rep.b #$20
  lda.w #$2102
  sta.l $7F01B2
  lda.w #$2119
  sta.l $7F01B4
  ; One four-character music value, highlighted like the other custom fields.
  lda.w $1EF2
  and.w #$00FF
  cmp.w #$0007
  bne custom_music_unfocused
  lda.w #$0400
  bra custom_music_palette
custom_music_unfocused:
  lda.w #$0000
custom_music_palette:
  sta.b $00
  lda.w $1EA9
  and.w #$00FF
  asl A
  asl A
  asl A
  tax
  lda.l $9C9060,X
  ora.b $00
  sta.l $7F046A
  lda.l $9C9062,X
  ora.b $00
  sta.l $7F046C
  lda.l $9C9064,X
  ora.b $00
  sta.l $7F046E
  lda.l $9C9066,X
  ora.b $00
  sta.l $7F0470
  sep.b #$20
  lda.w $1EF0
  bne custom_two_columns_done
  rep.b #$20
  ldx.w #$0000
  lda.w #$2000
custom_hide_second_column:
  sta.l $7F01B2,X
  sta.l $7F0232,X
  sta.l $7F0272,X
  sta.l $7F02B2,X
  sta.l $7F0332,X
  sta.l $7F0370,X
  sta.l $7F03F2,X
  inx
  inx
  cpx.w #$0006
  bne custom_hide_second_column
custom_two_columns_done:
  rep.b #$20
  ply
  plx
  plp
  rtl
org $9C8200
solo_results_template:
  php
  rep.b #$20
  phx
  ldx.w #$0000
solo_results_copy:
  lda.l $9C9800,X
  sta.l $7F0000,X
  inx
  inx
  cpx.w #$0780
  bne solo_results_copy
  plx
  plp
  rtl

org $9C8400
draw_normal_frames:
  php
  rep.b #$30
  phx
  phy
  ; Keep the normal menu's unused palette 4 synchronized with native palette 2
  ; border animation, preserving palette 0's white text in mixed border tiles.
  lda.w $1548
  cmp.w $1588
  bne normal_focus_colors
  lda.w $154A
  cmp.w $158A
  bne normal_focus_colors
  lda.w $154C
  cmp.w $158C
  beq normal_focus_cells
normal_focus_colors:
  lda.w $1548
  sta.w $1588
  lda.w $154A
  sta.w $158A
  lda.w $154C
  sta.w $158C
  sep.b #$20
  lda.b #$01
  sta.w $1DC2
  rep.b #$20
normal_focus_cells:
  lda.w $1EF1
  and.w #$00FF
  sta.b $02
  ldx.w #$0000
normal_frame_cell:
  lda.l $9C9100,X
  cmp.w #$FFFF
  beq normal_frames_done
  tay
  sep.b #$20
  lda.l $9C9102,X
  cmp.b $02
  rep.b #$20
  bne normal_frame_unfocused
  lda.w #$1000
  bra normal_frame_set
normal_frame_unfocused:
  lda.w #$0000
normal_frame_set:
  sta.b $00
  phx
  tyx
  lda.l $7F0000,X
  and.w #$E3FF
  ora.b $00
  sta.l $7F0000,X
  plx
  inx
  inx
  inx
  bra normal_frame_cell
normal_frames_done:
  ply
  plx
  plp
  rtl

org $9C8219
solo_results_scores:
  php
  rep.b #$20
  phx
  ldx.w #$000C
solo_results_move:
  lda.l $7F0198,X
  sta.l $7F01A2,X
  lda.l $7F01D8,X
  sta.l $7F01E2,X
  lda.l $7F0258,X
  sta.l $7F0262,X
  lda.l $7F0298,X
  sta.l $7F02A2,X
  lda.l $7F0318,X
  sta.l $7F0322,X
  lda.l $7F0358,X
  sta.l $7F0362,X
  lda.l $7F0498,X
  sta.l $7F04A2,X
  lda.l $7F04D8,X
  sta.l $7F04E2,X
  dex
  dex
  bpl solo_results_move
  ldx.w #$0000
  lda.w #$2000
solo_results_clear:
  sta.l $7F0198,X
  sta.l $7F01D8,X
  sta.l $7F0258,X
  sta.l $7F0298,X
  sta.l $7F0318,X
  sta.l $7F0358,X
  sta.l $7F0498,X
  sta.l $7F04D8,X
  inx
  inx
  cpx.w #$000A
  bne solo_results_clear
  plx
  plp
  rtl
