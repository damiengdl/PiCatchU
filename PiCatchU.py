#
# PiCatchU.py
# D. Gautier de Lahaut for a Surveillance system based on Raspberry Pi


import RPi.GPIO as GPIO
import time
import wget
import os
import sys

# Configure the Pi to use the BCM (Broadcom) pin names, rather than the pin positions
GPIO.setmode(GPIO.BCM)

user = 'xxxx'
password = 'xxxxxx'
user_chez_free = 'xxxxxx'
pasword_sms_chez_free = 'xxxxxxxx'
addressCam = ['Unused','192.168.0.xx', '192.168.0.xx']
addressNAS  = '192.168.0.xx'

surv_state = 0 # etat initial du systeme de surveillance
ready_to_send_life_sms = 1 # flag pour gerer l'envoi d'un SMS journalier
yellow_pin = 23
led_pin = 24

GPIO.setup(yellow_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(led_pin, GPIO.OUT)

def allume_led():
    GPIO.output(led_pin, True)

def eteint_led():
    GPIO.output(led_pin, False)

def clignote_led(nb_seconds):
    cpt = 0
    while (cpt < nb_seconds):
        GPIO.output(led_pin, True)
        time.sleep(0.2)
        GPIO.output(led_pin, False) 
        time.sleep(0.2)
        cpt = cpt + 0.4

def switch_ON_Cam(Cam):
    urlCam = 'http://'+user+':'+password+'@'+addressCam[Cam]+'/setSystemMotion?ReplySuccessPage=motion.htm&ReplyErrorPage=motion.htm&MotionDetectionEnable=1&MotionDetectionScheduleDay=0&MotionDetectionScheduleMode=0&MotionDetectionSensitivity=80&ConfigSystemMotion=Save'
    output = 'ON_CAM' + str(Cam) + '_' + time.strftime("%d%m%Y_%H:%M:%S")
    try:
        wget.download(urlCam,output)
    except Exception as e:
        print 'PiCatchU Exception switch_ON_Cam' + str(Cam) + ' ' + str(e) 

def switch_OFF_Cam(Cam):
    urlCam = 'http://'+user+':'+password+'@'+addressCam[Cam]+'/setSystemMotion?ReplySuccessPage=motion.htm&ReplyErrorPage=motion.htm&MotionDetectionEnable=0&MotionDetectionScheduleDay=0&ConfigSystemMotion=Save'
    output = 'OFF_CAM' + str(Cam) + '_' + time.strftime("%d%m%Y_%H:%M:%S")
    try:
        wget.download(urlCam,output)
    except Exception as e:
        print 'PiCatchU Exception switch_OFF_Cam' + str(Cam) + ' ' + str(e) 

def envoi_sms(Message):
    urlSMS = 'https://smsapi.free-mobile.fr/sendmsg?user=' + user_chez_free + '&pass=' + pasword_sms_chez_free + '&msg='+Message
    output = 'SEND_SMS_'+ Message.replace(" ","") + '_' + time.strftime("%d%m%Y_%H:%M:%S")
    try:
        wget.download(urlSMS,output)
    except Exception as e:
        print 'PiCatchU Exception envoi_sms_journalier ' + str(e) 

def envoi_sms_journalier():
        envoi_sms('PiCatchU%20Systeme%20Camera%20OK')
        
def envoi_sms_detection():
        envoi_sms('PiCatchU%20Detection%20Camera')


ready_to_send_life_sms = 1     
nb_files_before=-1    # compte le nombre de fichiers de detection sur le NAS
timeref = time.time() # timeref et timenow permettent de gerer un timer 
#print "Timeref = " + str(timeref)
while True:

    #******************************************
    # Gestion du recepteur 433 Mgz via le GPIO
    #******************************************

    #print("Yellow button value: yellow=" + str(GPIO.input(yellow_pin)))
    if GPIO.input(yellow_pin):
        if surv_state == 0:
            clignote_led(20)
            if GPIO.input(yellow_pin): # entre temps on a pu eteindre le recepteur
                surv_state = 1
                allume_led()
                print 'PiCatchU: Activation du systeme de surveillance ' + time.strftime("%d%m%Y_%H:%M:%S")
                sys.stdout.flush()
                switch_ON_Cam(1)
                switch_ON_Cam(2)
    else: # GPIO de yellow_pin est a 0
        if surv_state == 1:
            surv_state = 0
            eteint_led()
            print 'PiCatchU: Desactivation du systeme de surveillance ' + time.strftime("%d%m%Y_%H:%M:%S")
            sys.stdout.flush()
            switch_OFF_Cam(1)
            switch_OFF_Cam(2)
            nb_files_before=-1   
    time.sleep(0.5)             # delay 0.5 seconds

    #*********************************************************
    # Gestion de l'envoi du SMS journalier de vie du PiCatchU
    #*********************************************************
    heure = time.localtime()
    #print "Heure =" + str(heure.tm_hour) + " minutes=" + str(heure.tm_min) + " ready_to_send_life_sms=" + str(ready_to_send_life_sms)
    if (ready_to_send_life_sms == 1 and heure.tm_hour == 15 and heure.tm_min == 7):
        print 'PiCatchU: Envoi de SMS a Damien pour dire que tout va bien ' + time.strftime("%d%m%Y_%H:%M:%S")
        sys.stdout.flush()
        envoi_sms_journalier()                    
        ready_to_send_life_sms = 0
    if (heure.tm_hour == 15 and heure.tm_min == 10):
        ready_to_send_life_sms = 1

    #***************************************************************************************
    # Gestion de la detection de nouveaux fichiers des cameras sur le NAS pour envoi de SMS
    #***************************************************************************************
    timenow = time.time()
    if (surv_state == 1 and timenow > timeref + 20):
        timeref = timenow
        #print "PiCatchU: Test de presence de fichiers sur le NAS"
        sys.stdout.flush()

        pp = os.popen ("ssh "+addressNAS+" ls -l /Partage/Cam1|wc -l","r") ; 
        for line in pp.readlines() : 
            nb_files = int(line)
        pp.close () ; 
             
        pp = os.popen ("ssh "+addressNAS+" ls -l /Partage/Cam2|wc -l","r") ; 
        for line in pp.readlines() : 
            nb_files = nb_files + int(line)
        pp.close () ; 
        print 'PiCatchU: Nombre de lignes dans les repertoires Cam1 et Cam2 = ' + str(nb_files) + ' ' + time.strftime("%d%m%Y_%H:%M:%S") ;
        sys.stdout.flush()
                    
        if (nb_files_before != -1 and nb_files_before < nb_files):
            print "PiCatchU: Envoi de SMS de detection a Damien " +  time.strftime("%d%m%Y_%H:%M:%S")
            sys.stdout.flush()
            envoi_sms_detection()
            timeref = timenow + 60
                        
        nb_files_before = nb_files
        
