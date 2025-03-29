import marimo

__generated_with = "0.11.20"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import os 
    import sys
    sys.path.append(os.path.realpath(os.path.curdir))

    import mdpd
    from make_audios import SpeechGenerator, normalize_filename
    import soundfile as sf
    import random
    from tqdm import tqdm
    from IPython.display import Audio, display
    return (
        Audio,
        SpeechGenerator,
        display,
        mdpd,
        mo,
        normalize_filename,
        os,
        random,
        sf,
        sys,
        tqdm,
    )


@app.cell
def _(SpeechGenerator):
    speechGenerator = SpeechGenerator()
    return (speechGenerator,)


@app.cell
def _(Audio, display, speech_generator):
    def _():
        import numpy as np
        import soundfile as sf
        import re
        from nltk.tokenize import sent_tokenize

        gen_conversation_input = '''Teo: Hello.
        Ty: Hi, [Tẹo](/teo6/). It's me.
        Teo: Huh. who is this?
        Ty: It's me! [Tý](/ti5/) here.
        Ty: I just got a new phone number.
        Teo: Oh, [Tý](/ti5/). What's up?
        Ty: Can you help me with my homework?
        Teo: Sure, but I'm a bit busy right now.
        Teo: Can you give me an email?
        Ty: What's your email address?
        Teo: It's T E O at gmail dot com.
        '''

        gen_conversation_input = '''Teo: Hello.
    Ty: Hi, Teeoh. It's me.
    Teo: Huh, who is this?
    Ty: It's me! Tee here.
    Ty: I just got a new phone number.
    Teo: Oh, Tee. What's up?
    Ty: Can you help me with my homework?
    Teo: Sure, but I'm a bit busy right now.
    Teo: Can you give me an email?
    Ty: What's your email address?
    Teo: It's teeoh at gmail dot com.
    Ty: Huh? Can you repeat that?
    Teo: It’s t e o at gmail dot com!
    '''

        conversation = []

        for line in gen_conversation_input.split("\n"):
            line = line.strip()
            if len(line) == 0:
                continue
            speaker, text = line.split(": ")
            conversation.append((speaker, text))

        speechs = []
        speed = 1

        voice_map = {
            'Ty': 'af_heart',
            'Teo': 'am_eric'
        }

        for i, (speaker, text) in enumerate(conversation):
            sen_audios = []

            voice = speech_generator.get_voice(voice_map[speaker])

            sentences = text.split('. ')
            sentences = [text]

            for j, sentence in enumerate(sentences):
                # print(sentence, j)
                begin_duration=0
                if i == 2 and j==1:
                    print(sentence)
                    begin_duration=0.2
                sentence_audio = speech_generator.generate(
                    sentence, voice, speed=float(speed), begin_duration=begin_duration
                )

                sen_audios.append(sentence_audio)

            line = np.zeros(1)

            for sen_audio in sen_audios:
                line = np.concatenate((line, sen_audio), axis=0)
                line = np.concatenate((line, np.zeros((int(0.0 * 24000)))), axis=0)
            speechs.append(
                {
                    "audio": line,
                    "name": f"{i}_{speaker}",
                }
            ) 
        return speechs


    speechs = _()

    for speech in speechs:
      display(Audio(speech['audio'], rate=24000))
    return speech, speechs


@app.cell
def _(Audio, display, sf, speech_generator):
    for v in ["am_michael", "af_heart"]:
        save_path = f"processed_lessions/lession-2/pronun_audios/{v}.wav"
        example_line = "like a super Mario level. Like it's very like high detail. And like, once you get into the park, it just like, everything looks like a computer game and they have all these, like, you know, if, if there's like a, you know, like in a Mario game, they will have like a question block. And if you like, you know, punch it, a coin will come out. So like everyone, when they come into the park, they get like this little bracelet and then you can go punching question blocks around."
        example_audio = speech_generator.generate(
            example_line, speech_generator.get_voice(v), speed=1, begin_duration=0
        )
    
        sf.write(save_path, example_audio, 24000)

        display(Audio(example_audio, rate=24000))
    return example_audio, example_line, save_path, v


@app.cell
def _(os, sf, speechs):
    def _():
        save_dir = "processed_lessions/lession-2/pronun_audios/"
        os.makedirs(save_dir, exist_ok=True)
        for speech in speechs:
            sf.write(f"{save_dir}{speech['name']}.wav", speech['audio'], 24000)


    _()
    return


@app.cell
def _(mo):
    mo.md(r"""## Vocabularies""")
    return


@app.cell
def _(mo):
    mo.md(r"""### Prepare data""")
    return


@app.cell
def _(mdpd):
    vocab_table_str = '''
    | Word/ Phrase | IPA | Context | Meaning |
    | :---: | :---: | ----- | :---: |
    | Email | /ˈiːmeɪl/ | Một tin nhắn điện tử được gửi qua internet. | Thư điện tử |
    | Email address | /ˈiːmeɪl əˈdrɛs/ | Địa chỉ điện tử để gửi và nhận email. | Địa chỉ email |
    | Letter | /ˈlɛtər/ | Một tin nhắn viết tay hoặc đánh máy gửi qua đường bưu điện | Lá thư |
    | Instant  | /ˈɪnstənt/ | không cần chờ đợi hoặc trì hoãn. | Ngay lập tức |
    | Message/ text | /ˈmɛsɪdʒ/ /tekst/ | Một đoạn văn bản ngắn gửi qua điện thoại hoặc internet. | Tin nhắn |
    | instant message/ Instant text | /ˈɪnstənt ˈmɛsɪdʒ/ \- /ˈɪnstənt tekst/ | giao tiếp nhanh qua mạng, giữa người gửi và người nhận  | Tin nhắn tức thì |
    | send | /sɛnd/ | chuyển thông tin, vật phẩm hoặc dữ liệu từ một người đến một người khác | Gửi |
    | send a text/ letter/ message | /sɛnd ə tekst/ \- /lɛtər/ \- /mɛsɪdʒ/ | chuyển nội dung viết tay hoặc văn bản kỹ thuật số từ bạn đến người khác  | Gửi tin nhắn/ thư |
    | Meet | /miːt/ | cùng xuất hiện ở một địa điểm nào đó để trò chuyện, làm việc | Gặp gỡ |
    | in person | /ɪn ˈpɜːrsən/ | gặp gỡ người khác ở ngoài đời | Trực tiếp |
    | Meet/ see in person | /miːt ɪn ˈpɜːrsən/ | Gặp mặt ai đó ngoài đời thực, không qua điện thoại hoặc internet. | Gặp trực tiếp |
    | Video chat | /ˈvɪdi.oʊ tʃæt/ | Cuộc trò chuyện có sử dụng video qua internet. | Trò chuyện video |
    | Have a video chat with SO | /hæv ə ˈvɪdi.oʊ tʃæt wɪð ˈsʌmbədi/ | sử dụng công nghệ để giao tiếp với ai đó bằng cả hình ảnh và âm thanh, | Gọi video với ai đó |
    | Social network/ social media | /ˈsoʊʃl ˈnɛtˌwɜːrk/ | Các nền tảng trực tuyến để giao tiếp và kết nối với mọi người. | Mạng xã hội |
    | Use social network/ social media | /juːz ˈsoʊʃl ˈnɛtˌwɜːrk/ \- /juːz ˈsoʊʃl ˈmiːdiə/ | truy cập vào các nền tảng trực tuyến để tương tác với người khác | Sử dụng mạng xã hội |
    | Talk on the phone | /tɔːk ɑːn ðə foʊn/ | Cuộc trò chuyện giữa hai người qua điện thoại. | Nói chuyện qua điện thoại |
    | Username | /ˈjuːzərneɪm/ | danh tính cá nhân trên mạng | Tên người dùng |'''

    vocab_table = mdpd.from_md(vocab_table_str)
    vocab_table
    return vocab_table, vocab_table_str


@app.cell
def _(vocab_table):
    english = []
    vietnamese = []
    for i, x in vocab_table.iterrows():
        english.append(x['Word/ Phrase'])
        vietnamese.append(x['Meaning'])

    cleaned_english = [
        'Email.',
        'Email address',
        'Letter.',
        'Instant',
        'Message <br> text',
        'instant message <br> Instant text',
        'send',
        'send a text <br> send a letter <br> send a message',
        'Meet',
        'in person',
        'Meet in person <br> see in person',
        'Video chat',
        'Have a video chat with SO',
        'Social network <br> social media',
        'Use social network <br> Use social media',
        'Talk on the phone',
        'Username'
    ]

    cleaned_vietnamese = [
        'Thư điện tử.', 
        'Địa chỉ email.', 
        'Lá thư.', 
        'Ngay lập tức.', 
        'Tin nhắn.', 
        'Tin nhắn tức thì.', 
        'Gửi.', 
        'Gửi tin nhắn. Gửi thư.', 
        'Gặp gỡ.', 
        'Trực tiếp.', 
        'Gặp trực tiếp.', 
        'Trò chuyện video.', 
        'Gọi video với ai đó.', 
        'Mạng xã hội.', 
        'Sử dụng mạng xã hội.', 
        'Nói chuyện qua điện thoại.', 
        'Tên người dùng.'
    ]
    return cleaned_english, cleaned_vietnamese, english, i, vietnamese, x


@app.cell
def _():
    ### Generate English sound
    return


@app.cell
def _(SpeechGenerator, cleaned_english, normalize_filename, os, random, tqdm):
    speech_generator = SpeechGenerator()

    random.seed(118)
    def make_english_sounds():
        voices = {
            # "af_nicole": speech_generator.get_voice("af_nicole"),
            # "af_heart": speech_generator.get_voice("af_heart"),
            # "am_michael": speech_generator.get_voice("am_michael"),
            # "am_puck": speech_generator.get_voice("am_puck"),
            # "am_onyx": speech_generator.get_voice("am_onyx"),
            # "am_adam": speech_generator.get_voice("am_adam"),
            "af_sarah": speech_generator.get_voice("af_sarah"),
            # "af_bella": speech_generator.get_voice("af_bella"),
            "af_bella&am_michael": speech_generator.mix_voice(
                "af_bella", "am_michael", 0.5
            ),
        }

        english_audio = {}

        save_path = '../static/audio/lession-2/english'

        os.makedirs(save_path, exist_ok=True)

        for i, text in tqdm(enumerate(cleaned_english)):
            path = f"{save_path}/{normalize_filename(text)}.mp3"
            voice = random.choice(list(voices.keys()))
            print(voice)
            speech_generator.generate(
                text, voices[voice], save_path=path, speed=0.8, begin_duration=0.5, silent_duration=0.2
            )

            english_audio[i] = path
        return english_audio

    english_audio = make_english_sounds()
    return english_audio, make_english_sounds, speech_generator


@app.cell
def _(mo):
    mo.md(r"""### Generate Vietnamese sounds""")
    return


@app.cell
def _():
    # from transformers import VitsModel, AutoTokenizer
    # import torch
    # import numpy as np

    # model = VitsModel.from_pretrained("facebook/mms-tts-vie")
    # tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
    return


@app.cell
def _(cleaned_vietnamese, normalize_filename, os, tqdm):
    from gtts import gTTS

    def generate_vie_sound(text, save_path=None, begin_duration=0.5, silent_duration=0.4):
        # segments = text.split('<br>')
        # feq = 0

        # final_audio = np.zeros((1, int(begin_duration * 16000)))

        # for segment in segments:
        #     inputs = tokenizer(segment, return_tensors="pt")
        #     with torch.no_grad():
        #         output = model(**inputs).waveform

        #     final_audio = np.concatenate((final_audio, output.cpu()), axis=1)
        #     final_audio = np.concatenate(
        #         (final_audio, np.zeros((1, int(silent_duration * 16000)))), axis=1
        #     )
        # # final_audio = final_audio.squeeze()
        # if save_path:
        #     return sf.write(save_path, final_audio[0], 16000)
        # return final_audio

        tts = gTTS(text, lang="vi")
        tts.save(save_path)

    # generate_vie_sound("Xin chào <br> Tôi tên là việt.", "test_vie.mp3")

    def make_vietnamese_sounds():
        vietnamese_audio = {}

        save_path = '../static/audio/lession-2/vietnamese'

        os.makedirs(save_path, exist_ok=True)

        for i, text in tqdm(enumerate(cleaned_vietnamese)):
            path = f"{save_path}/{normalize_filename(text)}.mp3"
            generate_vie_sound(
                text, save_path=path
            )

            vietnamese_audio[i] = path

        return vietnamese_audio

    vietnamese_audio = make_vietnamese_sounds()
    return gTTS, generate_vie_sound, make_vietnamese_sounds, vietnamese_audio


@app.cell
def _(mo):
    mo.md(r"""### Generate Table""")
    return


@app.cell
def _(vocab_table):
    vocab_table
    return


@app.cell
def _(english_audio, vietnamese_audio, vocab_table):
    en_audio_buttons = []
    vi_audio_buttons = []
    for indx, row in vocab_table.iterrows():
        # print(english_audio[indx], vietnamese_audio[indx], vocab_table.keys())
        eng_text = row['Word/ Phrase']
        vie_text = row['Meaning']
        en_audio_buttons.append("{{" + f'<audio-player src="{english_audio[indx]}">' + "}} " + eng_text)
        vi_audio_buttons.append("{{" + f'<audio-player src="{vietnamese_audio[indx]}">' + "}} " + vie_text)

    new_vocab_table = vocab_table.copy()
    new_vocab_table['Word/ Phrase'] = en_audio_buttons
    new_vocab_table['Meaning'] = vi_audio_buttons
    print(new_vocab_table.to_markdown(index=False))
    return (
        en_audio_buttons,
        eng_text,
        indx,
        new_vocab_table,
        row,
        vi_audio_buttons,
        vie_text,
    )


@app.cell
def _(mo):
    mo.md(r"""### Generate conversation""")
    return


if __name__ == "__main__":
    app.run()
