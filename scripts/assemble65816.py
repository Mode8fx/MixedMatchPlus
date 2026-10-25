"""Dependency-free assembler for the explicit-width 65816 source used by this patch.

Supports labels, org, db/dw/dl, and the addressing modes in snes_disasm. Immediate
widths must be explicit (.b/.w); other memory operands default to absolute (.w).
"""
import re
from snes_disasm import OPS, SIZES, offset


def assemble(source: str) -> tuple[dict[int, bytes], dict[str, int]]:
    labels={}; result={}
    def value(expr, unresolved=False):
        expr=re.sub(r'\$([0-9a-fA-F]+)',r'0x\1',expr)
        try:return int(eval(expr,{'__builtins__':{}},labels))
        except NameError:
            if unresolved:return 0
            raise
    for phase in (0,1):
        pc=0; result={}
        for line_no,line in enumerate(source.splitlines(),1):
            line=line.split(';')[0].strip()
            if not line:continue
            if line.endswith(':'):
                labels[line[:-1]]=pc;continue
            parts=line.split(None,1);op=parts[0].lower();arg=parts[1].strip() if len(parts)>1 else ''
            try:
                if op=='org':pc=value(arg);continue
                if op in ('db','dw','dl'):
                    size={'db':1,'dw':2,'dl':3}[op]
                    data=b''.join((value(e,phase==0)&((1<<size*8)-1)).to_bytes(size,'little') for e in arg.split(','))
                else:
                    name,*width=op.split('.');width=width[0] if width else 'w';name=name.upper()
                    expr=arg;mode=''
                    if name in ('BRA','BPL','BMI','BNE','BEQ','BCS','BCC','BVS','BVC'):mode='r'
                    elif name in ('BRL','PER'):mode='rr'
                    elif arg.startswith('#'):
                        expr=arg[1:];mode='x' if name in ('LDX','LDY','CPX','CPY') else 'q' if name in ('REP','SEP','BRK','COP','WDM') else 'm'
                    elif arg.upper()=='A':mode='a';expr=''
                    elif arg:
                        if arg.endswith(',X') or arg.endswith(',x'):
                            expr=arg[:-2];mode={'b':'dx','w':'wx','l':'lx'}[width]
                        elif arg.endswith(',Y') or arg.endswith(',y'):
                            expr=arg[:-2];mode='dy' if width=='b' else 'wy'
                        else:mode={'b':'d','w':'w','l':'l'}[width]
                    opcode=OPS.index((name,mode))
                    count=(1 if width=='b' else 2) if mode in ('m','x') else SIZES[mode]
                    operand=value(expr,phase==0) if expr else 0
                    if mode in ('r','rr'):
                        operand-=pc+1+count
                        if phase and not -(1<<(8*count-1))<=operand<(1<<(8*count-1)):
                            raise ValueError('Branch out of range')
                    data=bytes([opcode])+(operand&((1<<count*8)-1)).to_bytes(count,'little')
                for i,b in enumerate(data):
                    if pc+i in result:raise ValueError('Overlapping output')
                    result[pc+i]=b
                pc+=len(data)
            except Exception as e:
                raise ValueError(f'Assembly line {line_no}: {line}: {e}') from e
    spans={};start=None;last=None;data=bytearray()
    for addr,b in sorted(result.items()):
        if last is None or addr!=last+1:
            if start is not None:spans[start]=bytes(data)
            start=addr;data=bytearray()
        data.append(b);last=addr
    if start is not None:spans[start]=bytes(data)
    return spans,labels
