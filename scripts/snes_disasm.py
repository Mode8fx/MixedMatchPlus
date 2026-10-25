"""Small 65816 disassembler for inspecting this ROM and Mesen register traces."""
from pathlib import Path
import argparse

ROWS = [
"BRK:q ORA:ix COP:q ORA:s TSB:d ORA:d ASL:d ORA:dl PHP ORA:m ASL:a PHD TSB:w ORA:w ASL:w ORA:l",
"BPL:r ORA:iy ORA:i ORA:sy TRB:d ORA:dx ASL:dx ORA:dly CLC ORA:wy INC:a TCS TRB:w ORA:wx ASL:wx ORA:lx",
"JSR:w AND:ix JSL:l AND:s BIT:d AND:d ROL:d AND:dl PLP AND:m ROL:a PLD BIT:w AND:w ROL:w AND:l",
"BMI:r AND:iy AND:i AND:sy BIT:dx AND:dx ROL:dx AND:dly SEC AND:wy DEC:a TSC BIT:wx AND:wx ROL:wx AND:lx",
"RTI EOR:ix WDM:q EOR:s MVP:b EOR:d LSR:d EOR:dl PHA EOR:m LSR:a PHK JMP:w EOR:w LSR:w EOR:l",
"BVC:r EOR:iy EOR:i EOR:sy MVN:b EOR:dx LSR:dx EOR:dly CLI EOR:wy PHY TCD JML:l EOR:wx LSR:wx EOR:lx",
"RTS ADC:ix PER:rr ADC:s STZ:d ADC:d ROR:d ADC:dl PLA ADC:m ROR:a RTL JMP:wi ADC:w ROR:w ADC:l",
"BVS:r ADC:iy ADC:i ADC:sy STZ:dx ADC:dx ROR:dx ADC:dly SEI ADC:wy PLY TDC JMP:wix ADC:wx ROR:wx ADC:lx",
"BRA:r STA:ix BRL:rr STA:s STY:d STA:d STX:d STA:dl DEY BIT:m TXA PHB STY:w STA:w STX:w STA:l",
"BCC:r STA:iy STA:i STA:sy STY:dx STA:dx STX:dy STA:dly TYA STA:wy TXS TXY STZ:w STA:wx STZ:wx STA:lx",
"LDY:x LDA:ix LDX:x LDA:s LDY:d LDA:d LDX:d LDA:dl TAY LDA:m TAX PLB LDY:w LDA:w LDX:w LDA:l",
"BCS:r LDA:iy LDA:i LDA:sy LDY:dx LDA:dx LDX:dy LDA:dly CLV LDA:wy TSX TYX LDY:wx LDA:wx LDX:wy LDA:lx",
"CPY:x CMP:ix REP:q CMP:s CPY:d CMP:d DEC:d CMP:dl INY CMP:m DEX WAI CPY:w CMP:w DEC:w CMP:l",
"BNE:r CMP:iy CMP:i CMP:sy PEI:i CMP:dx DEC:dx CMP:dly CLD CMP:wy PHX STP JMP:wl CMP:wx DEC:wx CMP:lx",
"CPX:x SBC:ix SEP:q SBC:s CPX:d SBC:d INC:d SBC:dl INX SBC:m NOP XBA CPX:w SBC:w INC:w SBC:l",
"BEQ:r SBC:iy SBC:i SBC:sy PEA:w SBC:dx INC:dx SBC:dly SED SBC:wy PLX XCE JSR:wix SBC:wx INC:wx SBC:lx",
]
OPS=[tuple((s+':').split(':')[:2]) for row in ROWS for s in row.split()]
SIZES={k:1 for k in ('q','d','dx','dy','ix','i','iy','s','sy','dl','dly','r')}
SIZES.update({k:2 for k in ('w','wx','wy','wi','wix','wl','rr','b')})
SIZES.update(l=3,lx=3,a=0,**{'':0})


def offset(pc):return ((pc>>16)&0x7f)*0x8000+(pc&0x7fff)


def instruction(rom,pc,ps=0x30):
    off=offset(pc);op=rom[off];name,mode=OPS[op]
    count=(1 if ps & (0x20 if mode=='m' else 0x10) else 2) if mode in ('m','x') else SIZES[mode]
    raw=rom[off:off+count+1];value=int.from_bytes(raw[1:],'little');arg=f'${value:0{count*2}X}'
    if mode in ('m','x','q'):arg='#'+arg
    elif mode=='a':arg='A'
    elif not mode:arg=''
    elif mode in ('r','rr'):
        signed=value-(1<<(count*8)) if value>>(count*8-1) else value
        arg=f'${(pc&0xff0000)|((pc+len(raw)+signed)&0xffff):06X}'
    elif mode in ('dx','wx','lx'):arg+=',X'
    elif mode in ('dy','wy'):arg+=',Y'
    elif mode in ('ix','wix'):arg='('+arg+',X)'
    elif mode in ('i','wi'):arg='('+arg+')'
    elif mode=='iy':arg='('+arg+'),Y'
    elif mode=='dl':arg='['+arg+']'
    elif mode=='dly':arg='['+arg+'],Y'
    elif mode=='s':arg+=',S'
    elif mode=='sy':arg='('+arg+',S),Y'
    return len(raw),f'{pc:06X} {raw.hex(" "):12} {name} {arg}'.rstrip()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('start',nargs='?',default='808000');p.add_argument('end',nargs='?',default='808100');p.add_argument('--ps',default='30');p.add_argument('--trace',type=Path);p.add_argument('--unique',action='store_true');a=p.parse_args()
    rom=(Path(__file__).resolve().parents[1]/'original_roms'/'Tetris & Dr. Mario (USA).sfc').read_bytes()
    if a.trace:
        seen=set()
        for line in a.trace.read_text().splitlines():
            vals=line.split();pc=int(vals[1],16);ps=int(vals[6],16)
            if pc&0xffff<0x8000:continue
            if a.unique and pc in seen:continue
            seen.add(pc)
            print(instruction(rom,pc,ps)[1]+'  '+ ' '.join(vals[2:]))
    else:
        pc=int(a.start,16);ps=int(a.ps,16)
        while pc<int(a.end,16):
            n,s=instruction(rom,pc,ps);print(s)
            if rom[offset(pc)]==0xc2:ps&=~rom[offset(pc)+1]
            if rom[offset(pc)]==0xe2:ps|=rom[offset(pc)+1]
            pc+=n


if __name__=='__main__':main()
