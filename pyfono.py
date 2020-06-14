#!/usr/bin/env python2

from __future__ import print_function
from pydbus import SystemBus, SessionBus
from gi.repository import GLib
import subprocess
#import hildon

global net_status
global net_params

new_sms_sound = '/usr/share/sounds/ui-new_email.wav'
incoming_call_sound = '/usr/share/sounds/ui-wake_up_tune.wav'

net_params = {}

def get_modem():
    # We don't expect to have more than one modem
    return sysbus.get('org.ofono','/').GetModems()[0][0]

def incoming_sms(s, a):
    # s is a str that contains the message text
    # a is a dict that contains time & sender
    #
    notice.Notify('', 0, 'general_sms', a['Sender'], s, [], {}, 0)
    subprocess.call(['/usr/bin/aplay', new_sms_sound])
    print(a['Sender'], ":", s)


def incoming_flash_msg(s, a):
    # s is a str that contains the message text
    # a is a dict that contains time & sender
    #
    # NOTE: I haven't tested flash messages!
    # using aplay since hildon module, which provides
    # hildon_play_system_sound, clashes with gi.repository
    notice.SystemNoteDialog(s, 0, '')
    subprocess.call(['/usr/bin/aplay', new_sms_sound])

def ussd_note(s):
    notice.SystemNoteDialog(s, 0, '')

def incoming_call(o, a):
    # o is the ofono path for the call
    # a contains the call details
    #
    notice.Notify('', 0, 'general_call', 'Incoming Call', \
            a['LineIdentification'], [], {}, 0)
    subprocess.call(
            ['/usr/bin/aplay', incoming_call_sound]\
            )
    print("Call from ", a['LineIdentification'])

def ended_call(o):
    pass

def setup_internet(s, v):
    global net_status
    global net_params

    if (type(v) is dict) and (len(v) > 0):
        net_params = v
        
        ipaddr = net_params.get('Address')
        netmask = net_params.get('Netmask')
        if "Gateway" in net_params.keys():
            gw = net_params.get('Gateway')
        else:
            gw = ''
        method = net_params.get('Method')
        iface = net_params.get('Interface')
        dns = net_params.get('DomainNameServers')

        # Check if there are other properties
        # If method = dhcp, request dhcp parameters

        try:
            subprocess.call(["/usr/bin/sudo","/bin/ip","address","add",str(ipaddr) + "/" + str(netmask), "dev", str(iface)])
            if len(gw) == 0:
                subprocess.call(["/usr/bin/sudo","/bin/ip","route","add","default","dev",str(iface)])
            else:
                # The gateway doesn't seem to work; using iface
                subprocess.call(["/usr/bin/sudo","/bin/ip","route","add","default","dev",str(iface)])
                # subprocess.call(["/usr/bin/sudo","/bin/ip","route","add","default","via",str(gw),"dev",str(iface)])
            with open("/home/user/.dns", "w") as f:
                for ns in range(len(dns)):
                    f.write("nameserver " + dns[ns] + "\n")
            subprocess.call(["/usr/bin/sudo","/bin/mv","/home/user/.dns", "/etc/resolv.conf"])
            
            print("Internet up")
        except:
            print("Parameters were already set??")

    elif v == False:
        print("Internet brought down")
        try:
            ret = subprocess.call(["/usr/bin/sudo","/bin/ip","address","del", str(net_params.get("Address"))+"/"+str(net_params.get("Netmask")), "dev", str(net_params.get("Interface"))])
        except:
            print("Could not manually flush old ip")

sysbus = SystemBus()
sessbus = SessionBus()

notice = sessbus.get('org.freedesktop.Notifications','/org/freedesktop/Notifications')

if __name__ == "__main__":
    modem = get_modem()
    ofonoModem = sysbus.get('org.ofono', modem)

    # Handle Incoming SMS & Flash/Instant Messages
    ofonoModem.IncomingMessage.connect(incoming_sms)
    ofonoModem.ImmediateMessage.connect(incoming_flash_msg)

    # Handle Phone Calls
    ofonoModem.CallAdded.connect(incoming_call)
    ofonoModem.CallRemoved.connect(ended_call)

    # Handle USSD Notifications
    # ofonoModem.NotificationReceived(ussd_note)

    # Set Internet Settings; assume 1 context 
    if len(ofonoModem.GetContexts()[0][0]) > 0:
        internet_ctx = ofonoModem.GetContexts()[0][0]
        ofono_ctx = sysbus.get('org.ofono', internet_ctx)
        ofono_ctx.PropertyChanged.connect(setup_internet)

    loop = GLib.MainLoop()
    loop.run()

