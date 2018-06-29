
from django.http import HttpResponse
from django.shortcuts import render, render_to_response
from django.views.decorators.csrf import csrf_exempt
from watson_developer_cloud import ToneAnalyzerV3
import subprocess
import sys
import glob
import serial
import serial.tools.list_ports



def index(request):
    usn, passw, vers = get_API_credential()
    myports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
    myports = [port[0] for port in myports]
    return render(request, 'index.html', {'usn': usn, 'passw': passw, 'vers': vers, 'serialport': myports, })


@csrf_exempt
def detectEmotion(request):
    try:
        data = str(request.POST.get('textInput'))
        port = str(request.POST.get('comPort'))
        username, password, version = get_API_credential()
        print(data, port)
        tone_analyzer = ToneAnalyzerV3(
            username=username,
            password=password,
            version=version
        )
        content_type = 'application/json'
        tone = tone_analyzer.tone({"text": data}, content_type)
        print(tone)
        emotion = tone['document_tone']['tones'][0]['tone_name']
        print(emotion)
        #score = tone['document_tone']['tones'][0]['score']
        em = ['Left', 'Right', 'Forward', 'Backward', 'Stop']
        dt = ['Joy', 'Anger', 'Fear', 'Sadness', 'Others']
        if str(emotion) in dt:
            command = dt.index(str(emotion))
        else:
            command = 4
        data = command
        command = em[command]
        if senddata(port, int(data) + 1) is True:
            print("Command sent - " + str(data))
        else:
            command = "NULL"
        return HttpResponse("Command Sent : <b>" + str(command) + "</b><br/>Emotion Detected : <b>" + str(emotion) + " </b>")
    except Exception as e:
        print(e)
        return HttpResponse("False")


def senddata(port, data):
    try:
        ser = serial.Serial(port, 38400, timeout=1)
        ser.close()
        ser.open()
        ser.write(str(data).encode())
        ser.close()
    except serial.SerialException:
        return False
    return True


def get_API_credential():
    fp = open('media/API.txt', 'r')
    usn = fp.readline()
    passw = fp.readline()
    vers = fp.readline()
    fp.close()
    print(usn )
    return usn, passw, vers


@csrf_exempt
def set_API_credential(request):
    try:
        if request.method == 'POST' and request.is_ajax:
            print(request.POST)
            username = request.POST.get('username')
            password = request.POST.get('password')
            version = request.POST.get('version')
            print(username, password, version, "this is it")
            tone_analyzer = ToneAnalyzerV3(
                username=username,
                password=password,
                version=version
            )
            tone = tone_analyzer.tone(tone_input="I am feeling hungry, I am angry, get out", content_type="text/plain")
            print(tone)
            fp = open('media/API.txt', 'w+')
            fp.writelines(username + "\n")
            fp.writelines(password + "\n")
            fp.writelines(version)
            fp.close()
        else:
            return HttpResponse("False")
    except Exception as e:
        print(e)
        return HttpResponse("False")
    return HttpResponse("True", {'Cusername': username, 'passw': password, 'vers': version})


