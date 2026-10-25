"""Headless Mesen CPU trace/RAM snapshots for ROM research (workspace copy of Mesen)."""
import argparse
from pathlib import Path
import subprocess
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name',default='trace')
    p.add_argument('--rom',type=Path,default=ROOT/'original_roms'/'Tetris & Dr. Mario (USA).sfc')
    p.add_argument('--sequence',nargs='+',default=['600','start:1','120','down:1','1','start:1','120','start:1','120'])
    p.add_argument('--trace',nargs=2,type=int,default=[0,0])
    p.add_argument('--dumps',nargs='+',type=int)
    p.add_argument('--writes',nargs='*',default=[],help='Test-only WRAM edits: decimal-frame:hex-address:hex-byte')
    p.add_argument('--mesen',type=Path,default=Path('C:/RetroBat/emulators/mesen/Mesen.exe'),help='Installed Mesen to copy into custom/tools on first use')
    a=p.parse_args(); frame=0; inputs=[]
    for token in a.sequence:
        if ':' in token:
            button,count=token.split(':');count=int(count)
            inputs.append(f'{{{frame},{frame+count},"{button}"}}')
        else:count=int(token)
        frame+=count
    dumps=a.dumps or [frame]
    folder=ROOT/'custom'/'research';folder.mkdir(parents=True,exist_ok=True)
    writes=[]
    for item in a.writes:
        f,addr,val=item.split(':');writes.append(f'{{{int(f)},{int(addr,16)},{int(val,16)}}}')
    config=('return {name='+json.dumps(a.name)+f',frames={frame},trace_start={a.trace[0]},trace_end={a.trace[1]},'
            +'inputs={'+','.join(inputs)+'},dumps={'+','.join(f'[{f}]=true' for f in dumps)
            +'},writes={'+','.join(writes)+'}}')
    (folder/'trace_config.lua').write_text(config)
    runner=folder/'trace_run.lua'
    runner.write_text('RESEARCH_BASE='+json.dumps(folder.as_posix()+'/')+'\n'+(ROOT/'scripts'/'trace_rom.lua').read_text())
    local=ROOT/'custom'/'tools'/'mesen';exe=local/'Mesen.exe'
    if not exe.exists():
        local.mkdir(parents=True,exist_ok=True)
        for name in ('Mesen.exe','MesenCore.dll','libHarfBuzzSharp.dll','libSkiaSharp.dll'):
            shutil.copyfile(a.mesen.parent/name,local/name)
        settings=json.loads((a.mesen.parent/'settings.json').read_text(encoding='utf-8-sig'))
        settings['Debug']['ScriptWindow']['AllowIoOsAccess']=True
        (local/'settings.json').write_text(json.dumps(settings))
    r=subprocess.run([str(exe),'--testrunner',str(a.rom.resolve()),str(runner),'--enableStdout','--timeout=60'],capture_output=True,text=True,timeout=70,cwd=ROOT)
    print(r.stdout); print('Exit',r.returncode)
    if r.returncode:print(r.stderr);raise SystemExit(r.returncode)


if __name__=='__main__':main()
