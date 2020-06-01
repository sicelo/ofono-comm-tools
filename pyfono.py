#!/usr/bin/env python2

from __future__ import print_function
from pydbus import SystemBus, SessionBus
from gi.repository import GLib
import subprocess
#import hildon
#import osso

def getModem():
    # We don't expect to have more than one modem
    return sysbus.get('org.ofono','/').GetModems()[0][0]

def inMsg(s, a):
    # s is a str that contains the message text
    # a is a dict that contains time & sender
    #
    # would be nice to figure out how to use 'actions' for launching UI to show the message
    ret = notice.Notify('', 0, 'general_sms', a['Sender'], s, \
            ['default','some-action'], {}, 0\
            )
    # print(ret)
    subprocess.call(['/usr/bin/aplay','/usr/share/sounds/ui-new_email.wav'])


def inFlashMsg(s, a):
    # s is a str that contains the message text
    # a is a dict that contains time & sender
    #
    # NOTE: I haven't tested this!
    # would be nice to figure out how to use 'actions' for launching UI to show the message
    ret = notice.SystemNoteDialog(s, 0, '')
    # print(ret)
    subprocess.call(['/usr/bin/aplay','/usr/share/sounds/ui-new_email.wav'])

def inCall(o, a):
    # o is ..
    #print(a.items())
    #hildon.hildon_play_system_sound('/usr/share/sounds/ui-wake_up_tune.wav')
    #
    # using aplay since hildon module seems to clash with gi.repository
    ret = notice.Notify('', 0, 'general_call', 'Incoming Call', \
            a['LineIdentification'], ['default','some-action'], {}, 0\
            )
    subprocess.call(
            ['/usr/bin/aplay','/usr/share/sounds/ui-wake_up_tune.wav']\
            )

def endedCall(o):
    #print("Call ended")
    #hildon.hildon_play_system_sound('/usr/share/sounds/ui-default_beep.wav')
    subprocess.call(
            ['/usr/bin/aplay','/usr/share/sounds/ui-default_beep.wav']\
            )

sysbus = SystemBus()
sessbus = SessionBus()

notice = sessbus.get('org.freedesktop.Notifications','/org/freedesktop/Notifications')



if __name__ == "__main__":
    modem = getModem()
    ofonoModem = sysbus.get('org.ofono', modem)

    # Handle Incoming SMS & Flash/Instant Messages
    ofonoModem.IncomingMessage.connect(inMsg)
    ofonoModem.ImmediateMessage.connect(inFlashMsg)

    # Handle Phone Calls
    ofonoModem.CallAdded.connect(inCall)
    ofonoModem.CallRemoved.connect(endedCall)

    loop = GLib.MainLoop()
    loop.run()
