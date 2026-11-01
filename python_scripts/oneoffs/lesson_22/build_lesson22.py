#!/usr/bin/env python3
"""Build Lesson 22 content/audio from raw Markdown and recordings."""
import html
import json
import re
import subprocess
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/"python_scripts/raw_lessons/LESSON-22"
SRC=next(RAW.glob("*.md"))
DEST=ROOT/"frontend/static/audio/lesson-22"
PAGE=ROOT/"frontend/content/docs/topic_6/lesson-22.md"
SOURCE=SRC.read_text().replace("\\!","!").replace("\\$","$").replace("\\+","+")

def tidy(s):
    return re.sub(r"\\([.*_])",r"\1",s).strip().replace("**","").strip()

def cells(line):
    return [tidy(c) for c in line.strip().strip("|").split("|")]

def table_after(key):
    pos=SOURCE.find(key)
    if pos<0: raise ValueError(key)
    lines=SOURCE[pos:].splitlines()
    start=next(i for i,line in enumerate(lines) if line.startswith("|"))
    out=[]
    for line in lines[start:]:
        if not line.startswith("|"): break
        cc=cells(line)
        if re.fullmatch(r"[-: ]+",cc[0]):continue
        out.append(cc)
    return out

voc=table_after("1\\. Vocabulary")
if not voc or not voc[0][0].isdigit():
    voc=[row for row in table_after("1\\. Vocabulary") if row[0].isdigit()]
else: voc=[row for row in voc if row[0].isdigit()]
boost1=table_after("| Bargaining for a lower price")
boost2=table_after("| Suggesting a different price")
practice=table_after("3. **Let’s Practice")[0]
think=table_after("4\\. Think and speak")
think=[row for row in think if row[0] in ("Bo","Na")]
conversation=table_after("**1\\. Conversation**")
conversation=[row for row in conversation if row[0] in ("Bo","Na")]
questions=table_after("Listen carefully and answer the questions:")
questions=[row for row in questions if len(row)==2 and row[0] not in ("Question","-----")]
assert len(voc)==22 and len(think)==11 and len(conversation)==11 and len(questions)==5,(len(voc),len(think),len(conversation),len(questions))
assert [r[2] for r in think]==[r[1] for r in conversation]
print("Parsed",len(voc),"vocabs,",len(think),"dialogue lines,",len(questions),"questions",flush=True)

def key(s):
    import unicodedata
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    return re.sub("[^a-z0-9]+","_",s).strip("_")

def audio(src,text):
    return '{{< audio-text text="'+html.escape(text,quote=True)+'" src="audio/lesson-22/'+src+'" >}}'
def controls(src):
    return '{{< audio-with-controls src="audio/lesson-22/'+src+'" >}}'
def head(label,path,level,anchor=""):
    return '{{< header-audio text="'+html.escape(label,quote=True)+'" src="'+path+'" level="'+str(level)+'"'+(f' id="{anchor}"' if anchor else "")+' >}}'

def rows_and_audio():
    counters=defaultdict(int)
    vi=[]; en=[]
    for sp,vi_text,en_text in think:
        counters[sp]+=1
        fn=f"{sp}{counters[sp]}.mp3"
        vi.append(dict(type="dialogue",speaker=sp,text=vi_text,en=en_text,audio=fn))
        en.append(dict(type="dialogue",speaker=sp,text=en_text,audio=fn))
    for folder,data in (("think-and-speak",vi),("conversation",en)):
        path=DEST/folder/"conversation.json";path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    return en

EN=rows_and_audio()
parts=[
'---\ntitle: "Lesson 22: WILL YOU TAKE $20?"\ndescription: "Bargaining for a lower price and suggesting a different price."\nlead: "English for The Blind - Lesson 22"\ndraft: false\nweight: 920\nseo:\n  title: "EFTB - Lesson 22: Will You Take $20?"\n  description: "Learn to bargain and suggest a different price in English."\nhide_title: true\n---',
head("Lesson 22: Will You Take $20?","audio/lesson-22/title.mp3",1),controls("focus/eng/audio.mp3"),
"**Lesson Focus**\n\n- Bargaining for a lower price\n- Suggesting a different price",
"---\n\n## Section 1 {#section-1 .toc-only}",
head("Section 1","audio/common/headers/section_1.mp3",2,"section-1"),
"### 1. Vocabulary {#vocabulary .toc-only}",
head("1. Vocabulary","audio/common/headers/1_vocabulary.mp3",3,"vocabulary"),
'<table><thead><tr><th>No</th><th>Word / Phrase</th><th>IPA</th><th>Part of speech</th><th>Meaning</th></tr></thead><tbody>'
]
jobs_en=[("Lesson twenty two. Will you take twenty dollars?","title.mp3"),
("Lesson focus. Bargaining for a lower price. Suggesting a different price.","focus/eng/audio.mp3")]
jobs_vi=[]
for n,word,ipa,pos,meaning in voc:
    slug=key(word);a=f"vocabs/eng/{slug}.mp3";b=f"vocabs/vie/{slug}.mp3"
    parts.append(f"<tr><td>{n}</td><td>{audio(a,word)}</td><td>{html.escape(ipa)}</td><td>{html.escape(pos)}</td><td>{audio(b,meaning)}</td></tr>")
    jobs_en.append((word,a));jobs_vi.append((meaning,b))
parts+=['</tbody></table>',"### 2. Language Booster {#language-booster .toc-only}",head("2. Language Booster","audio/common/headers/2_language_booster.mp3",3,"language-booster"),'<table><thead><tr><th>Structure</th><th>Example</th><th>Meaning</th></tr></thead><tbody>']
for group_no,(label,group) in enumerate((("Bargaining for a lower price",boost1),("Suggesting a different price",boost2)),1):
    parts.append(f'<tr><th colspan="3">{audio(f"sentences/group_{group_no}.mp3",label)}</th></tr>')
    jobs_en.append((label,f"sentences/group_{group_no}.mp3"))
    pattern=""
    pat_n=0
    for row in group:
        if len(row)<3:continue
        structure,english,vietnamese=row[:3]
        if not english or english in (":----","-----"):continue
        if structure and structure not in ("Bargaining for a lower price","Suggesting a different price"):
            pattern=structure;pat_n+=1
            spoken_pattern = pattern.replace("it/them", "it or them").replace("+", " plus ")
            jobs_en.append((spoken_pattern,f"sentences/pattern_{group_no}_{pat_n}.mp3"))
        if not pattern:continue
        n=sum(1 for p in parts if f"sentences/en_{group_no}_{pat_n}_" in p)+1
        pa=f"sentences/en_{group_no}_{pat_n}_{n}.mp3";pb=f"sentences/vi_{group_no}_{pat_n}_{n}.mp3"
        parts.append("<tr><td>"+(audio(f"sentences/pattern_{group_no}_{pat_n}.mp3", pattern) if structure else "")+"</td><td>"+audio(pa,english)+"</td><td>"+audio(pb,vietnamese)+"</td></tr>")
        jobs_en.append((english,pa));jobs_vi.append((vietnamese,pb))
parts+=['</tbody></table>',"### 3. Let's Practice {#lets-practice .toc-only}",head("3. Let's Practice","audio/common/headers/3_lets_practice.mp3",3,"lets-practice")]
practice_text="Take turns bargaining for a lower price for the items below."
parts.append(audio("lets_practice/instructions.mp3",practice_text));jobs_en.append((practice_text,"lets_practice/instructions.mp3"))
parts.append("<table><tbody><tr>")
for i,item in enumerate(practice,1):
    if item:
        path=f"lets_practice/item_{i}.mp3";parts.append(f"<td>{audio(path,item)}</td>");jobs_en.append((item,path))
parts.append("</tr></tbody></table>")
parts+=["### 4. Think and Speak {#think-and-speak .toc-only}",head("4. Think and Speak","audio/common/headers/4_think_and_speak.mp3",3,"think-and-speak"),"**Ngữ cảnh:**",controls("context/vie/context.mp3")]
context=SOURCE.split("**Context:",1)[1].split("**",1)[0].strip()
parts.append(context)
parts.append('{{< audio_script_table json="/audio/lesson-22/think-and-speak/conversation.json" audiopath="/audio/lesson-22/think-and-speak/" headerSpeaker="Character" headerText="Vietnamese" headerMeaning="English" meaningField="en" >}}')
parts+=["---\n\n## Section 2 {#section-2 .toc-only}",head("Section 2","audio/common/headers/section_2.mp3",2,"section-2"),"### 1. Conversation {#conversation .toc-only}",head("1. Conversation","audio/common/headers/1_conversation.mp3",3,"conversation"),'{{< audio_script_table json="/audio/lesson-22/conversation/conversation.json" audiopath="/audio/lesson-22/conversation/" headerSpeaker="Character" headerText="English" meaningField="" >}}',"#### Listening Comprehension {#listening-comprehension .toc-only}",head("Listening Comprehension","audio/common/headers/listening_comprehension.mp3",4),head("Listen carefully and answer the questions:","audio/common/headers/listen_carefully_and_answer_the_questions.mp3",5),"<table><thead><tr><th>Question</th><th>Answer</th></tr></thead><tbody>"]
for i,(q,a) in enumerate(questions,1):
    qa=f"comprehension/q{i}.mp3";aa=f"comprehension/a{i}.mp3"
    parts.append(f"<tr><td>{audio(qa,str(i)+'. '+q)}</td><td>{audio(aa,a)}</td></tr>")
    jobs_en.extend([(str(i)+". "+q,qa),(a,aa)])
parts+=["</tbody></table>","#### Listening and Speaking {#listening-and-speaking .toc-only}",head("Listening and Speaking","audio/common/headers/listening_and_speaking.mp3",4)]
instr="Listen to the audio and imitate the speaker's pronunciation, rhythm, and intonation."
parts.append(controls("pronunciation/instructions.mp3"));parts.append(instr);jobs_en.append((instr,"pronunciation/instructions.mp3"))
parts+=["### 2. Application {#application .toc-only}",head("2. Application","audio/lesson-22/application/title.mp3",3,"application")]
jobs_en.append(("Two. Application","application/title.mp3"))
app_instruction="Pair work. Work in pairs and create your own conversation. Take turns speaking and try to use the structures you have learned."
parts.append(controls("application/instructions.mp3"));parts.append("**PAIR WORK:** "+app_instruction);jobs_en.append((app_instruction,"application/instructions.mp3"))
topic="Topic: Let's Have a Yard Sale!"
description="Imagine you are having a yard sale with a friend. One of you is the seller, and the other is the buyer. Take turns choosing items, asking about prices, and bargaining for a better deal. Try to agree on a price for each item."
parts.append(head(topic,"audio/lesson-22/application/topic.mp3",4,"yard-sale"));parts.append(controls("application/description.mp3"));parts.append(description)
jobs_en.extend([(topic,"application/topic.mp3"),(description,"application/description.mp3")])
includes=["Asking about prices and offering items for sale.","Bargaining for a lower price.","Suggesting a different price and agreeing on a final price."]
parts.append(audio("application/includes.mp3","Your conversation should include:"));jobs_en.append(("Your conversation should include:","application/includes.mp3"))
for i,txt in enumerate(includes,1):
    parts.append("- "+audio(f"application/include_{i}.mp3",txt));jobs_en.append((txt,f"application/include_{i}.mp3"))
examples=["How much is this desk lamp?","I'm selling it for 100,000 dong.","Will you take 60,000 dong?","I can give it to you for 80,000 dong.","How about 70,000 dong?","All right! It's a deal!"]
parts.append(audio("application/prompts.mp3","Example prompts:"));jobs_en.append(("Example prompts:","application/prompts.mp3"))
for i,txt in enumerate(examples,1):
    parts.append("- "+audio(f"application/example_{i}.mp3",txt));jobs_en.append((txt,f"application/example_{i}.mp3"))
PAGE.write_text("\n\n".join(parts)+"\n")
for row in EN: jobs_en.append((row["text"],"conversation/"+row["audio"]))
(DEST/"jobs.json").write_text(json.dumps({"english":jobs_en,"vietnamese":jobs_vi,"context":context},ensure_ascii=False,indent=2))
print("Page:",PAGE,"English jobs:",len(jobs_en),"Vietnamese jobs:",len(jobs_vi),flush=True)

def convert_recordings():
    archives=list(RAW.glob("*.zip"))
    assert len(archives)==1
    names=defaultdict(int)
    with zipfile.ZipFile(archives[0]) as z:
        recordings={}
        for name in z.namelist():
            base=Path(name).stem
            if base.startswith("Bo") and base[2:].isdigit():
                recordings[("Bo",int(base[2:]))]=name
            elif re.fullmatch(r"N\d+_2",base):
                recordings[("Na",int(base[1:].split("_")[0]))]=name
        assert len(recordings)==11, recordings.keys()
        for row in EN:
            names[row["speaker"]]+=1
            key=(row["speaker"],names[row["speaker"]])
            target=DEST/"think-and-speak"/row["audio"]
            if target.exists():continue
            with tempfile.TemporaryDirectory() as t:
                inp=Path(t)/"source.m4a";inp.write_bytes(z.read(recordings[key]))
                subprocess.run(["ffmpeg","-v","error","-y","-i",str(inp),"-codec:a","libmp3lame","-q:a","3",str(target)],check=True)
    print("Converted 11 supplied recordings",flush=True)

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="--recordings":convert_recordings()
