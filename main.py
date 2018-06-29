
from watson_developer_cloud import ToneAnalyzerV3
import json
import pyaudio
import wave
import io
from os.path import join, dirname
import speech_recognition as sr
r = sr.Recognizer()
#wf = wave.open('rem.wav', 'rb')
#with sr.WavFile("15.wav") as source:              # use "test.wav" as the audio source
 #   audio = r.record(source)                        # extract audio data from the file

#try:
 #   print("understanding audio")
 #   data = r.recognize_google(audio)                  # generate a list of possible transcriptions
   # print(data)
#except LookupError:                                 # speech is unintelligible
 #   print("Could not understand audio")
with sr.Microphone() as source:
    print("Say something!")
    audio = r.listen(source)

# recognize speech using Sphinx
tone_analyzer = ToneAnalyzerV3(
    username = "404c0d53-3afa-4c6a-8029-9abda9feb22f",
    password = "MTOG8sOMMPm4",
    version='2017-09-21     '
)
try:
    data=r.recognize_google(audio)
    print("Google Speech Recognition thinks you said                                   " + data)
    tone = tone_analyzer.tone(tone_input= data, content_type="text/plain")
    print(json.dumps(tone, indent=2))
   # with open('data.txt', 'w') as outfile:
    #json.dump(data, outfile,indent=2)
   # with io.open('data.json', 'w', encoding='utf8') as outfile:
    with open('data.txt', 'w') as outfile:
     json.dump(tone, outfile, sort_keys = True, indent = 4,
               ensure_ascii = False)
except sr.UnknownValueError:
    print("Google Speech Recognition could not understand audio                ")
except sr.RequestError as e:
    print("Could not request results from Google Speech Recognition service; {0}                  ".format(e))
