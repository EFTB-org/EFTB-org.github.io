#!/usr/bin/env python3
"""Generate missing Lesson 22 speech using Chatterbox (English) and gTTS (Vietnamese).
Bo conversation uses Lesson 20 Bo reference; other English uses Kore lesson reference.
"""
import json
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
DEST=ROOT/"frontend/static/audio/lesson-22"
DATA=json.loads((DEST/"jobs.json").read_text())
def valid(p):
    if not p.exists() or p.stat().st_size<1000:return False
    check=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],capture_output=True,text=True)
    try:return check.returncode==0 and float(check.stdout.strip())>0.25
    except ValueError:return False

def main():
    import sys
    stage=sys.argv[1] if len(sys.argv)>1 else "english"
    if stage=="vietnamese":
        from gtts import gTTS
        for n,(text,rel) in enumerate(DATA["vietnamese"],1):
            dest=DEST/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            if valid(dest):continue
            with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
                f=Path(tmp)/"output.mp3";gTTS(text,lang="vi").save(str(f))
                if not valid(f):raise RuntimeError(rel)
                f.replace(dest)
            print(f"Vietnamese {n}/{len(DATA['vietnamese'])}: {rel}",flush=True)
        return
    import torch,torchaudio
    from chatterbox.tts import ChatterboxTTS
    jobs=DATA["english"]
    if stage=="bo":jobs=[j for j in jobs if j[1].startswith("conversation/Bo")]
    elif stage=="english":jobs=[j for j in jobs if not j[1].startswith("conversation/Bo")]
    else:raise ValueError(stage)
    if not any(not valid(DEST/r) for t,r in jobs):return
    device="cuda" if torch.cuda.is_available() else "cpu"
    print("Loading Chatterbox on",device,flush=True)
    model=ChatterboxTTS.from_pretrained(device=device)
    if stage=="bo":
        source=ROOT/"frontend/static/audio/lesson-20/conversation"
        with tempfile.TemporaryDirectory() as tmp:
            reference=Path(tmp)/"bo.wav"
            cmd=["ffmpeg","-loglevel","error","-y"]
            for i in (2,3,5):cmd+=["-i",str(source/f"bo{i}.mp3")]
            cmd+=["-filter_complex","[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]","-map","[out]","-ac","1","-ar","24000",str(reference)]
            subprocess.run(cmd,check=True)
            model.prepare_conditionals(str(reference))
    else:
        model.prepare_conditionals(str(ROOT/"python_scripts/kore_audio_prompt.wav"))
    for n,(text,rel) in enumerate(jobs,1):
        dest=DEST/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if valid(dest):continue
        print(f"{stage} {n}/{len(jobs)}: {rel}",flush=True)
        with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
            wav=Path(tmp)/"clip.wav";mp3=Path(tmp)/"clip.mp3"
            parts=[];acc=""
            for word in text.split():
                if len(acc)+len(word)>108 and acc:parts.append(acc);acc=""
                acc=(acc+" "+word).strip()
            if acc:parts.append(acc)
            waves=[]
            for part in parts:
                waves.append(model.generate(part).cpu())
                if device=="cuda":torch.cuda.empty_cache()
            merged=[]
            for w in waves:
                if merged:merged.append(torch.zeros(w.shape[0],int(model.sr*0.14)))
                merged.append(w)
            torchaudio.save(str(wav),torch.cat(merged,dim=1),model.sr)
            subprocess.run(["ffmpeg","-loglevel","error","-y","-i",str(wav),"-codec:a","libmp3lame","-q:a","3",str(mp3)],check=True)
            if not valid(mp3):raise RuntimeError(rel)
            mp3.replace(dest)
if __name__=="__main__":main()
