; MixedMatchPlus native 65816 extensions. A=8-bit, X/Y=16-bit unless stated.
; $1EF0: 0=one player, 1=two players; $1EF1/$1EF2: added menu cursors.
; Existing menus/settings, game stages, timers, and rules remain the game engine's.

org $8AEA00
normal_init:
  inc.w $0305
  stz.w $1EF1
  lda.b #$01
  rtl
custom_init:
  inc.w $0305
  stz.w $1EF2
  lda.b #$00
  rtl

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
  jsr.w $E792
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
  dec.w $1EF2
custom_not_up:
  rep.b #$20
  lda.b $41
  bit.w #$0400
  sep.b #$20
  beq custom_not_down
  lda.w $1EF2
  cmp.b #$07
  beq custom_not_down
  inc.w $1EF2
custom_not_down:
  lda.w $1EF2
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
  lda.b $42
  and.b #$02
  beq custom_right
  jsr.w $E010
  bra custom_p2
custom_right:
  jsr.w $E02A
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
  beq normal_second_marker_done
  jsr.w $DF82
normal_second_marker_done:
  rts

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

org $9C8000
draw_normal_count:
  php
  rep.b #$20
  phx
  ldx.w #$0000
draw_normal_count_loop:
  lda.l $9C9000,X
  sta.l $7F0148,X
  inx
  inx
  cpx.w #$002A
  bne draw_normal_count_loop
  sep.b #$20
  lda.w $1EF0
  beq normal_highlight_one
  ldx.w #$0160
  bra normal_highlight
normal_highlight_one:
  ldx.w #$0148
normal_highlight:
  ldy.w #$0009
normal_highlight_loop:
  lda.l $7F0001,X
  ora.b #$04
  sta.l $7F0001,X
  inx
  inx
  dey
  bne normal_highlight_loop
count_draw_done:
  rep.b #$20
  plx
  plp
  rtl

draw_custom_count:
  php
  rep.b #$20
  phx
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
  sta.l $7F0172
  lda.w #$2119
  sta.l $7F0174
  sep.b #$20
  lda.w $1EF0
  bne custom_two_columns_done
  rep.b #$20
  ldx.w #$0000
  lda.w #$2000
custom_hide_second_column:
  sta.l $7F0172,X
  sta.l $7F0232,X
  sta.l $7F0272,X
  sta.l $7F02B2,X
  sta.l $7F03B2,X
  sta.l $7F03F2,X
  sta.l $7F04F2,X
  inx
  inx
  cpx.w #$0006
  bne custom_hide_second_column
custom_two_columns_done:
  rep.b #$20
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
