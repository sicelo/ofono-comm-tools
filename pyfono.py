#!/usr/bin/env python2

from __future__ import print_function
import dbus
import hildon
import gtk
import dbus.mainloop.glib
import gobject
import subprocess
import os

new_sms_sound = '/usr/share/sounds/ui-new_email.wav'
incoming_call_sound = '/usr/share/sounds/ui-wake_up_tune.wav'

alsa_temp = '/tmp/alsa.settings'
# using sound card settings for droid 4 provided by unicsy_demo application
# untested on N900 until libcmtspeech is working
devnull = open(os.devnull, 'w')
device = subprocess.call(['/bin/grep','RX-51','/proc/cpuinfo'], stdout=devnull, stderr=devnull)
if device == 1: # Assume Motorola Droid 4
    alsa_call = '/usr/share/unicsy/audio/motorola-xt894/alsa.playback.call.loud'
else:   # Nokia N900
    alsa_call = ''

net_params = {}

def call_note(call_id):
    window = hildon.StackableWindow()
    note = hildon.hildon_note_new_confirmation(window, call_id)
    note.set_button_texts("Answer", "Reject") 
    note.add_button("Send SMS", 1)
    note.add_button("Ignore", 2)
    response = gtk.Dialog.run(note)
    note.destroy()
    window.destroy()
    return response

def get_modem():
    # We don't expect to have more than one modem
    Manager = dbus.Interface(system.get_object('org.ofono','/'), 'org.ofono.Manager')
    return Manager.GetModems()[0][0]

def incoming_sms(s, a):
    # s is a str that contains the message text
    # a is a dict that contains time & sender
    #
    notifications_interface.Notify('', 0, 'general_sms', a.get('Sender'), s, [], {}, 0)
    hildon.hildon_play_system_sound(new_sms_sound)
    print(a.get('Sender'), ":", s)

def incoming_flash_msg(s, a):
    # s is a str that contains the message text
    # a is a dict that contains time & sender
    #
    # NOTE: I haven't tested flash messages!
    notifications_interface.SystemNoteDialog(s, 0, '')
    hildon.hildon_play_system_sound(new_sms_sound)
    print(a.get('Sender'), ":", s)

def ussd_note(s):
    notifications_interface.SystemNoteDialog(s, 0, '')
    print(s)

def phone_call(o, a):
    # o is the ofono path for the call
    # a contains the call details
    VoiceCall = dbus.Interface(system.get_object('org.ofono', o), 'org.ofono.VoiceCall')
    if str(a.get('State')) == "incoming":
        hildon.hildon_play_system_sound(incoming_call_sound)
        user_choice = call_note(str(a.get('LineIdentification')))
        if user_choice == 1:
            VoiceCall.Hangup()
            # 2. Open SMS application
        elif user_choice == 2:
            pass
            # 1.Silence the ringtone
        elif user_choice == -5:
            subprocess.call(['/usr/bin/sudo','/usr/sbin/alsactl','--file', alsa_temp, 'store'])
            if alsa_call != '':
                subprocess.call(['/usr/bin/sudo','/usr/sbin/alsactl','--file', alsa_call, 'restore'])
                VoiceCall.Answer()
            else:
                print("We are unable to setup this device's sound card. Call answered at own risk")
                VoiceCall.Answer()
        elif user_choice == -6:
            VoiceCall.Hangup()
    else:
        pass

def ended_call(o):
    if os.path.isfile(alsa_temp):
        subprocess.call(['/usr/bin/sudo','/usr/sbin/alsactl','--file', alsa_temp, 'restore'])
        subprocess.call(['/usr/bin/sudo','/bin/rm',alsa_temp])

def setup_internet(s, v):
    global net_params

    if type(v) is dbus.Dictionary and (v.get("Interface") is not None):
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
        if (subprocess.call(["/usr/bin/sudo","/bin/ip","address","flush", "dev", str(net_params.get("Interface"))], stdout=devnull, stderr=devnull)) != 0:
            print("Could not flush old IP.\nThis is likely not an error, but confirm if necessary")

if __name__ == "__main__":
    loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    system = dbus.SystemBus(mainloop=loop)
    session = dbus.SessionBus()

    notifications = session.get_object('org.freedesktop.Notifications','/org/freedesktop/Notifications')
    notifications_interface = dbus.Interface(notifications, dbus_interface='org.freedesktop.Notifications')
    
    Modem = get_modem()
    Modem_Proxy = system.get_object('org.ofono', Modem)

    # Handle Incoming SMS & Flash/Instant Messages
    system.add_signal_receiver(incoming_sms, signal_name="IncomingMessage", dbus_interface="org.ofono.MessageManager")
    system.add_signal_receiver(incoming_flash_msg, signal_name="ImmediateMessage", dbus_interface="org.ofono.MessageManager")

    # Handle Phone Calls
    system.add_signal_receiver(phone_call, signal_name="CallAdded", dbus_interface="org.ofono.VoiceCallManager")
    system.add_signal_receiver(ended_call, signal_name="CallRemoved", dbus_interface="org.ofono.VoiceCallManager")

    # Handle USSD Notifications
    # Modem.NotificationReceived(ussd_note)

    # Set Internet Settings; assume 1 context
    try:
        ConnectionManager = dbus.Interface(system.get_object('org.ofono', Modem), 'org.ofono.ConnectionManager')
        if len(ConnectionManager.GetContexts()[0][0]) > 0:
            internet_ctx = ConnectionManager.GetContexts()[0][0]
            ofono_ctx = system.get_object('org.ofono', internet_ctx)
            system.add_signal_receiver(setup_internet, signal_name="PropertyChanged", dbus_interface="org.ofono.ConnectionContext")
    except:
        print("No contexts defined")

    gobject.MainLoop().run()
