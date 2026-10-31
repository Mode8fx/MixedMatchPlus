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
  ; Keep the native held-direction delay/repeat. Start/back/navigation use
  ; press edges below; only setting changes consume the repeat-enabled mask.
  jsr.w $E268
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
  lda.w $1DD9
  bit.w #$0300
  sep.b #$20
  beq custom_p2
  lda.w $1EF2
  bne custom_setting
  lda.w $1DDA
  and.b #$01
  sta.w $1EF0
  bra custom_p2
custom_setting:
  cmp.b #$07
  beq custom_music_input
  lda.w $1DDA
  and.b #$02
  beq custom_right
  jsr.w $E010
  bra custom_p2
custom_right:
  jsr.w $E02A
  bra custom_p2
custom_music_input:
  lda.w $1DDA
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
  bcc solo_results_fade
  cmp.b #$06
  bcc solo_results_round
  beq solo_results_total
  cmp.b #$07
  bne solo_results_exit
  jmp.w solo_results_input
solo_results_exit:
  ; Same fade back to Mixed Match title as the original results screen.
  jsr.w $DADD
  brl.w solo_results_draw
solo_results_sound:
  jsr.w $D916
  brl.w solo_results_draw
solo_results_fade:
  jsr.w $D921
  brl.w solo_results_draw
solo_results_round:
  dec.w $0316
  beq solo_results_round_ready
  brl.w solo_results_draw
solo_results_round_ready:
  ldx.w #$0000
  stx.w $0B00
  lda.w $0305
  cmp.b #$04
  beq solo_results_round2
  cmp.b #$05
  beq solo_results_round3
  jsr.w $DC1F
  ldx.w #$0198
  bra solo_results_round_done
solo_results_round2:
  jsr.w $DC55
  ldx.w #$0258
  bra solo_results_round_done
solo_results_round3:
  jsr.w $DC92
  jsr.w $DD2D
  ldx.w #$0318
solo_results_round_done:
  jsl.l solo_results_scores
  lda.b #$3C
  sta.w $0316
  inc.w $0305
  stz.w $0306
  brl.w solo_results_draw
solo_results_total:
  lda.w $0306
  beq solo_results_total_wait
  cmp.b #$01
  beq solo_results_total_show
  dec.w $0316
  bne solo_results_draw
  inc.w $0305
  stz.w $0306
  brl.w solo_results_draw
solo_results_total_wait:
  dec.w $0316
  bne solo_results_draw
  inc.w $0306
  brl.w solo_results_draw
solo_results_total_show:
  ldx.w #$0000
  stx.w $0B00
  jsr.w $DCF7
  ldx.w #$0498
  jsl.l solo_results_scores
  lda.b #$3C
  sta.w $0316
  inc.w $0306
  brl.w solo_results_draw
solo_results_input:
  jsr.w $DEBF
  lda.w $0306
  bne solo_results_input_ready
  jsl.l solo_results_prompt
  inc.w $0306
  brl.w solo_results_draw
solo_results_input_ready:
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
  bne mixed_sprites_two
  jsl.l solo_shift_sprites
  rtl
mixed_sprites_two:
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
  bne solo_display_other
  lda.w $1EF0
  bne solo_display_other
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
  ; W1 is the full-screen animated opening. W2 is the centered playfield.
  ; BG2/BG3 (including the timer) use W1 alone; BG1/OBJ are visible only
  ; inside both W1 and W2. Thus every layer closes before any map reload.
  lda.b #$3F
  sta.w $2123
  lda.b #$0F
  sta.w $2125
  lda.b #$03
  sta.w $2124
  stz.w $212A
  stz.w $212B
  lda.b #$17
  sta.b $4D
  sta.b $4E
solo_display_other:
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
  ; Expand the native 128px opening to 256px, preserving its 64-frame
  ; close/open timing and logical counters. At 64/63, W1 is empty.
  lda.b $6C
  asl A
  sta.w $2126
  lda.b $6D
  asl A
  inc A
  sta.w $2127
  lda.w $1EF3
  sta.w $2128
  clc
  adc.b #$7F
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
  jsl.l timer_padding_display
  rep.b #$30
  ply
  plx
  pla
  plp
  rts

org $9C8500
timer_load:
  ; The native gold frame leaves palette-3 colors 9/10 unused. Give its paper
  ; the existing HUD white and its font shadow the exact Dr. Mario OBJ shade.
  rep.b #$20
  lda.w #$FFFF
  sta.w $1EFC
  lda.l $8394A4
  sta.w $1572
  lda.l $839506
  sta.w $1574
  sep.b #$20
  lda.b #$01
  sta.w $1DC2
  lda.w $1EF0
  bne timer_load_two_font
  jsl.l timer_solo_font_load
  bra timer_load_font_done
timer_load_two_font:
  lda.b #$9D
  pha
  pea.w $9000
timer_font_destination:
  pea.w $0000 ; Generated font span, including preserved interleaved native tiles.
timer_font_length:
  pea.w $0000
  jsl.l $808B0B
timer_load_font_done:
  jsl.l timer_border_load
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
  phb
  phx
  phy
  lda.b $00
  pha
  lda.b $02
  pha
  lda.b $04
  pha
  ; All layouts use BG2 column 13. Solo's native camera shifts Tetris by
  ; 80px and Dr. Mario by 72px: panel x=184 / 176, or x=104 in two-player.
  lda.w $1EF0
  and.w #$00FF
  beq timer_lookup_solo
  sep.b #$20
  lda.b #$9C
  bra timer_lookup_bank
timer_lookup_solo:
  sep.b #$20
  lda.b #$9E
timer_lookup_bank:
  pha
  plb
  rep.b #$20
  lda.w #$06ED
  sta.b $00
  cmp.w $1EFA
  beq timer_position_saved
  jsl.l solo_timer_cutout
timer_position_saved:
  lda.b $00
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
  ; Each half follows that player's stage. Solo mirrors P1's choice on both
  ; halves; two-player matches can show silver and gold simultaneously.
  lda.w $03F1
  and.w #$00FF
  cmp.w #$0003
  beq timer_left_doctor
  lda.w #$0000
  bra timer_left_style
timer_left_doctor:
  lda.w #$0400
timer_left_style:
  sta.w $1EF6
  lda.w $1EF0
  and.w #$00FF
  beq timer_solo_right_style
  lda.w $08F1
  and.w #$00FF
  cmp.w #$0003
  beq timer_right_doctor
  lda.w #$0000
  bra timer_right_style
timer_right_doctor:
  lda.w #$0400
  bra timer_right_style
timer_solo_right_style:
  lda.w $1EF6
timer_right_style:
  sta.w $1EF8
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
  clc
  adc.w $1EF6
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
  clc
  adc.w $1EF8
  sta.b $04
  ; Each style has a 32-byte frame record; copy only its player's half.
  lda.w $1EF6
  lsr A
  lsr A
  lsr A
  lsr A
  lsr A
  tax
  lda.w $9300,X
  sta.l $7F0D00
  lda.w $9302,X
  sta.l $7F0D02
  lda.w $9304,X
  sta.l $7F0D04
  lda.w $930C,X
  sta.l $7F0D24
  lda.w $930E,X
  sta.l $7F0D26
  lda.w $9310,X
  sta.l $7F0D28
  lda.w $1EF8
  lsr A
  lsr A
  lsr A
  lsr A
  lsr A
  tax
  lda.w $9306,X
  sta.l $7F0D06
  lda.w $9308,X
  sta.l $7F0D08
  lda.w $930A,X
  sta.l $7F0D0A
  lda.w $9312,X
  sta.l $7F0D2A
  lda.w $9314,X
  sta.l $7F0D2C
  lda.w $9316,X
  sta.l $7F0D2E
  ldx.b $02
  lda.w $A000,X
  sta.l $7F0D0C
  lda.w $A002,X
  sta.l $7F0D0E
  lda.w $A004,X
  sta.l $7F0D10
  lda.w $A006,X
  sta.l $7F0D18
  lda.w $A008,X
  sta.l $7F0D1A
  lda.w $A00A,X
  sta.l $7F0D1C
  ldx.b $04
  lda.w $A800,X
  sta.l $7F0D12
  lda.w $A802,X
  sta.l $7F0D14
  lda.w $A804,X
  sta.l $7F0D16
  lda.w $A806,X
  sta.l $7F0D1E
  lda.w $A808,X
  sta.l $7F0D20
  lda.w $A80A,X
  sta.l $7F0D22
  jsl.l timer_gold_refresh
  jsl.l timer_popup_prepare
  jsl.l timer_padding_prepare
  pla
  sta.b $04
  pla
  sta.b $02
  pla
  sta.b $00
  ply
  plx
  plb
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
  cmp.b #$04
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

; Relocate completed solo OAM while sprites are built, outside the next
; frame's vblank transfers. Long GAME-n cards must not consume the timer's
; upload budget. P2 continues through the untouched native renderer.
org $9C8800
solo_shift_sprites:
  php
  rep.b #$30
  phx
  pha
  sep.b #$20
  lda.b #$50
  ldx.w $03F1
  cpx.w #$0003
  bne solo_sprite_shift_ready
  lda.b #$48
solo_sprite_shift_ready:
  sta.w $1EF3
  ldx.w #$1900
solo_sprite_loop:
  cpx.w $1DC5
  bcs solo_sprite_done
  lda.b $00,X
  clc
  adc.w $1EF3
  sta.b $00,X
  inx
  inx
  inx
  inx
  bra solo_sprite_loop
solo_sprite_done:
  rep.b #$30
  pla
  plx
  plp
  rtl

org $9C8900
solo_timer_cutout:
  ; When the solo camera changes by 8px, clear the newly exposed column of
  ; the timer's BG3 cutout immediately. The staged full-map reload follows
  ; later; until then an old color tile would tint one edge of the panel.
  lda.w $1EF0
  and.w #$00FF
  beq solo_timer_cutout_check_ready
  rtl
solo_timer_cutout_check_ready:
  lda.w $1EF4
  and.w #$00FF
  bne solo_timer_cutout_build
  rtl
solo_timer_cutout_build:
  lda.w #$01FF
  sta.l $7F0D50
  sta.l $7F0D52
  sta.l $7F0D54
  sta.l $7F0D56
  lda.w #$1801
  sta.l $7F0D60
  lda.w #$0D50
  sta.l $7F0D62
  lda.w #$087F
  sta.l $7F0D64
  lda.w #$0000
  sta.l $7F0D66
  lda.w #$8100
  sta.l $7F0D68
  lda.b $00
  clc
  adc.w #$0400
  ldx.w $03F1
  cpx.w #$0003
  bne solo_timer_cutout_target
  clc
  adc.w #$0005
solo_timer_cutout_target:
  sta.l $7F0D67
  ; Append the native descriptor format without changing DB: bank $7F has
  ; no low-WRAM mirror for the engine's absolute queue-pointer accesses.
  ldx.w $1DC0
  cpx.w #$1BC0
  bcs solo_timer_cutout_done
  lda.l $7F0D60
  sta.b $28,X
  lda.l $7F0D62
  sta.b $2A,X
  lda.l $7F0D64
  sta.b $2C,X
  lda.l $7F0D66
  sta.b $2E,X
  lda.l $7F0D68
  sta.b $30,X
  txa
  clc
  adc.w #$000A
  sta.w $1DC0
solo_timer_cutout_done:
  rtl

; Alternate maps retain native backgrounds outside the compact 29px gold frame.
; BG2 uses unused VRAM $1800..$1FFF. BG3's two live rows occupy four reserved
; graphics slots at $8DC0/$8E80, using map base $8800. Channel 6 selects these
; maps on two scanlines above and one below the frame without touching scroll.
org $80D300
timer_padding_display:
  lda.w $0BAF
  cmp.b #$30
  bne timer_padding_disable
  lda.w $1EF4
  beq timer_padding_disable
  lda.w $1EF7
  ora.w $1EF9
  beq timer_padding_disable
  lda.w $1EFE
  bne timer_padding_enable
  ldx.w #$0801
  stx.w $4360
  ldx.w #$FE00
  stx.w $4362
  lda.b #$9C
  sta.w $4364
  lda.b #$01
  sta.w $1EFE
timer_padding_enable:
  lda.b $34
  ora.b #$40
  sta.b $34
  rtl
timer_padding_disable:
  lda.w $1EFE
  beq timer_padding_display_done
  stz.w $1EFE
  lda.b $34
  and.b #$BF
  sta.b $34
  ldx.w #$0804
  stx.w $2108
timer_padding_display_done:
  rtl

org $9C8A00
timer_padding_prepare:
  ; Record 0..2: solo phases. Records 3..11: P1 phase * 3 + P2 phase.
  lda.w $03F1
  and.w #$00FF
  dec A
  lsr A
  cmp.w #$0003
  bcc timer_padding_left_valid
  lda.w #$0000
timer_padding_left_valid:
  sta.b $00
  lda.w $1EF0
  and.w #$00FF
  beq timer_padding_key_ready
  lda.b $00
  asl A
  clc
  adc.b $00
  adc.w #$0003
  sta.b $00
  lda.w $08F1
  and.w #$00FF
  dec A
  lsr A
  cmp.w #$0003
  bcc timer_padding_right_valid
  lda.w #$0000
timer_padding_right_valid:
  clc
  adc.b $00
  sta.b $00
timer_padding_key_ready:
  lda.b $00
  jsl.l timer_border_prepare
  cmp.w $1EFC
  bne timer_padding_changed
  rtl
timer_padding_changed:
  sta.b $02
  asl A
  asl A
  clc
  adc.b $02
  asl A
  asl A
  asl A
  tax
  lda.w $1EF4
  and.w #$00FF
  beq timer_padding_initial_load
  ; Four 64-byte transfers only when either player's stage changes.
  ldy.w $1DC0
  cpy.w #$1BA0
  bcs timer_padding_prepare_done
  lda.w #$0014
  sta.b $04
timer_padding_queue_word:
  lda.l $9CFC00,X
  sta.w $0028,Y
  inx
  inx
  iny
  iny
  dec.b $04
  bne timer_padding_queue_word
  sty.w $1DC0
  lda.b $00
  sta.w $1EFC
timer_padding_prepare_done:
  rtl
timer_padding_initial_load:
; Initial copies run under the same forced blank as the native map loads.
  lda.b $00
  sta.w $1EFC
  sep.b #$20
  lda.b #$9C
  pha
  rep.b #$20
  lda.l $9CFC02,X
  pha
  pea.w $0EE0
  pea.w $0040
  sep.b #$20
  jsl.l $808B0B
  lda.b #$9C
  pha
  rep.b #$20
  lda.l $9CFC0C,X
  pha
  pea.w $0F40
  pea.w $0040
  sep.b #$20
  jsl.l $808B0B
  lda.b #$9C
  pha
  rep.b #$20
  lda.l $9CFC16,X
  pha
  pea.w $46E0
  pea.w $0040
  sep.b #$20
  jsl.l $808B0B
  lda.b #$9C
  pha
  rep.b #$20
  lda.l $9CFC20,X
  pha
  pea.w $4740
  pea.w $0040
  sep.b #$20
  jsl.l $808B0B
  rep.b #$20
  rtl

; Replace only the 16 static frame cells with the current layout's background
; composites. The eight numeral cells keep the shared native clock lookup.
org $9C8B00
timer_border_prepare:
  pha
  asl A
  asl A
  asl A
  asl A
  asl A
  tax
  lda.l $9C9400,X
  sta.l $7F0D00
  lda.l $9C9402,X
  sta.l $7F0D02
  lda.l $9C9404,X
  sta.l $7F0D04
  lda.l $9C9406,X
  sta.l $7F0D06
  lda.l $9C9408,X
  sta.l $7F0D08
  lda.l $9C940A,X
  sta.l $7F0D0A
  lda.l $9C940C,X
  sta.l $7F0D0C
  cpx.w #$0020
  beq timer_border_solo_right_top
  lda.l $9C940E,X
  sta.l $7F0D16
timer_border_solo_right_top:
  lda.l $9C9410,X
  sta.l $7F0D18
  cpx.w #$0020
  beq timer_border_solo_right_bottom
  lda.l $9C9412,X
  sta.l $7F0D22
timer_border_solo_right_bottom:
  lda.l $9C9414,X
  sta.l $7F0D24
  lda.l $9C9416,X
  sta.l $7F0D26
  lda.l $9C9418,X
  sta.l $7F0D28
  lda.l $9C941A,X
  sta.l $7F0D2A
  lda.l $9C941C,X
  sta.l $7F0D2C
  lda.l $9C941E,X
  sta.l $7F0D2E
  pla
  rtl

org $9C8C00
timer_border_load:
  lda.b #$9E
  pha
  pea.w $8000
timer_color_destination:
  pea.w $0000
timer_color_length:
  pea.w $0000
  jsl.l $808B0B
  ; Solo uses inactive P2's BG palette 7. Two-player uses only unused pens
  ; in native BG palettes 4/6, preserving both players' piece palettes.
  ; These combine gold rails with the native background strips.
  ; The already requested native palette DMA uploads these under forced blank.
  php
  rep.b #$30
  phx
  lda.w $1EF0
  and.w #$00FF
  beq timer_gold_solo_palette
  ldx.w #$000E
timer_gold_two_palette:
  lda.l $9C9620,X
  sta.w $1582,X
  dex
  dex
  bpl timer_gold_two_palette
  lda.l $9C9630
  sta.w $15C2
  lda.l $9C9632
  sta.w $15C6
  lda.l $9C9634
  sta.w $15C8
  lda.l $9C9636
  sta.w $15CA
  lda.l $9C9638
  sta.w $15CC
  ; BG3 palette 1 is unused by native art. Its colors supply the shared
  ; background tint (native 15/31 agree), plus orange/yellow subtraction
  ; from one light-gold main pen, preserving the exact original RGB values.
  lda.w $151E
  sta.w $150A
  lda.w #$58E0
  sta.w $150C
  lda.w #$4000
  sta.w $150E
  bra timer_gold_palette_done
timer_gold_solo_palette:
  ldx.w #$001E
timer_gold_solo_palette_loop:
  lda.l $9C9600,X
  sta.w $15E0,X
  dex
  dex
  bpl timer_gold_solo_palette_loop
timer_gold_palette_done:
  plx
  plp
  rtl

; Native stage loads replace palette slots. Repair only our unused pens and
; mirror the current BG3 tint before the next DMA. Stable frames upload nothing.
org $9C8D00
timer_gold_refresh:
  php
  rep.b #$30
  pha
  phx
  phy
  lda.w $1EF0
  and.w #$00FF
  bne timer_gold_refresh_check_style
  brl.w timer_gold_refresh_done
timer_gold_refresh_check_style:
  lda.w $1EF6
  ora.w $1EF8
  bne timer_gold_refresh_build
  brl.w timer_gold_refresh_done
timer_gold_refresh_build:
  ldy.w #$0000
  ldx.w #$000E
timer_gold_refresh_left:
  lda.l $9C9620,X
  cmp.w $1582,X
  beq timer_gold_refresh_left_next
  sta.w $1582,X
  iny
timer_gold_refresh_left_next:
  dex
  dex
  bpl timer_gold_refresh_left
  lda.l $9C9630
  cmp.w $15C2
  beq timer_gold_refresh_right_1
  sta.w $15C2
  iny
timer_gold_refresh_right_1:
  lda.l $9C9632
  cmp.w $15C6
  beq timer_gold_refresh_right_2
  sta.w $15C6
  iny
timer_gold_refresh_right_2:
  lda.l $9C9634
  cmp.w $15C8
  beq timer_gold_refresh_right_3
  sta.w $15C8
  iny
timer_gold_refresh_right_3:
  lda.l $9C9636
  cmp.w $15CA
  beq timer_gold_refresh_right_4
  sta.w $15CA
  iny
timer_gold_refresh_right_4:
  lda.l $9C9638
  cmp.w $15CC
  beq timer_gold_refresh_palette
  sta.w $15CC
  iny
timer_gold_refresh_palette:
  lda.w $151E
  cmp.w $150A
  beq timer_gold_refresh_tint_1
  sta.w $150A
  iny
timer_gold_refresh_tint_1:
  lda.w #$58E0
  cmp.w $150C
  beq timer_gold_refresh_tint_2
  sta.w $150C
  iny
timer_gold_refresh_tint_2:
  lda.w #$4000
  cmp.w $150E
  beq timer_gold_refresh_tint_done
  sta.w $150E
  iny
timer_gold_refresh_tint_done:
  cpy.w #$0000
  beq timer_gold_refresh_done
  sep.b #$20
  lda.b #$01
  sta.w $1DC2
  rep.b #$20
timer_gold_refresh_done:
  ply
  plx
  pla
  plp
  rtl

; The native Dr. Mario Game Over frame/text use BG palettes 4/6 too. Retain
; their exact pixels/colors in spare palette-1 pens while timer art is active.
; All work stays in game logic, before the existing BG1/palette DMA uploads.
org $9C8E00
timer_popup_prepare:
  php
  rep.b #$30
  pha
  phx
  phy
  lda.w $1EF0
  and.w #$00FF
  beq timer_popup_done
  lda.w $03F1
  and.w #$00FF
  cmp.w #$0003
  bne timer_popup_second
  lda.w $0305
  and.w #$00FF
  cmp.w #$0009
  bne timer_popup_second
  ldy.w #$0308
  jsr.w timer_popup_map
timer_popup_second:
  lda.w $08F1
  and.w #$00FF
  cmp.w #$0003
  bne timer_popup_done
  lda.w $0805
  and.w #$00FF
  cmp.w #$0009
  bne timer_popup_done
  ldy.w #$0328
  jsr.w timer_popup_map
timer_popup_done:
  ply
  plx
  pla
  plp
  rtl

timer_popup_map:
  lda.w #$0006
  sta.b $02
timer_popup_row:
  lda.w #$0008
  sta.b $00
timer_popup_cell:
  tyx
  lda.l $7F0000,X
  and.w #$E000
  sta.b $04
  lda.l $7F0000,X
  and.w #$1FFF
  pha
  and.w #$03FF
  sec
  sbc.w #$00BC
  cmp.w #$0014
  bcs timer_popup_skip
  asl A
  asl A
  tax
  pla
  cmp.l $9C9700,X
  bne timer_popup_next
  lda.l $9C9702,X
  ora.b $04
  tyx
  sta.l $7F0000,X
timer_popup_next:
  iny
  iny
  dec.b $00
  bne timer_popup_cell
  tya
  clc
  adc.w #$0030
  tay
  dec.b $02
  bne timer_popup_row
  ; Refresh only changed colors; native stage loads can replace palette 1.
  ldx.w #$0000
timer_popup_palette:
  lda.l $9C9750,X
  tay
  lda.l $9C9752,X
  cmp.w $1500,Y
  beq timer_popup_palette_next
  sta.w $1500,Y
  sep.b #$20
  lda.b #$01
  sta.w $1DC2
  rep.b #$20
timer_popup_palette_next:
  inx
  inx
  inx
  inx
  cpx.w #$0018
  bcc timer_popup_palette
  rts
timer_popup_skip:
  pla
  bra timer_popup_next

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
  lda.l $9C9000,X
  sta.l $7F0108,X
  inx
  inx
  cpx.w #$0030
  bne draw_custom_count_loop
  sep.b #$20
  lda.w $1EF0
  inc A
  sta.l $7F0120
  lda.w $1EF2
  bne custom_count_draw_done
  ; Only the count digit changes color; all fixed text stays white.
  lda.l $7F0121
  ora.b #$04
  sta.l $7F0121
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
  rep.b #$30
  phx
  phy
  ; X is the native first-row score destination. Copy backwards because
  ; centering overlaps that source; touch only the newly revealed score.
  txa
  clc
  adc.w #$000C
  tax
  ldy.w #$0007
solo_results_move:
  lda.l $7F0000,X
  sta.l $7F0008,X
  lda.l $7F0040,X
  sta.l $7F0048,X
  dex
  dex
  dey
  bne solo_results_move
  inx
  inx
  ldy.w #$0004
  lda.w #$2000
solo_results_clear:
  sta.l $7F0000,X
  sta.l $7F0040,X
  inx
  inx
  dey
  bne solo_results_clear
  ply
  plx
  plp
  rtl

org $9C8300
results_initial_map:
  lda.w $1EF0
  bne results_initial_map_upload
  ; Three result-only tiles preserve the native yellow 1P glyphs at a
  ; four-pixel offset. Native result graphics leave $1C0..$1FF unused.
  lda.b #$9C
  pha
  pea.w $90A0
  pea.w $2C00
  pea.w $0060
  jsl.l $808B0B
  jsl.l solo_results_template
results_initial_map_upload:
  jsl.l $809440
  rtl

solo_results_prompt:
  php
  rep.b #$30
  phx
  ldx.w #$0000
solo_results_prompt_copy:
  lda.l $9C9080,X
  sta.l $7F0614,X
  inx
  inx
  cpx.w #$0016
  bne solo_results_prompt_copy
  plx
  plp
  rtl

; Each player count has its own timer font/lookup set. Keep the same VRAM
; budget while permitting a one-pixel solo clock shift across tile boundaries.
org $9C8F00
timer_solo_font_load:
  lda.b #$9F
  pha
  pea.w $8000
timer_solo_font_destination:
  pea.w $0000
timer_solo_font_length:
  pea.w $0000
  jsl.l $808B0B
  rtl
