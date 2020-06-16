#!/usr/bin/env python2

from __future__ import print_function
import dbus
import hildon
import dbus.mainloop.glib
import gobject
import subprocess

new_sms_sound = '/usr/share/sounds/ui-new_email.wav'
incoming_call_sound = '/usr/share/sounds/ui-wake_up_tune.wav'

net_params = {}

def get_modem():
    # We don't expect to have more than one modem
    dbus_obj = system.get_object('org.ofono','/')
    Manager = dbus.Interface(dbus_obj, 'org.ofono.Manager')
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

def incoming_call(o, a):
    # o is the ofono path for the call
    # a contains the call details
    #
    notifications_interface.Notify('', 0, 'general_call', 'Incoming Call', \
            a['LineIdentification'], [], {}, 0)
    hildon.hildon_play_system_sound(incoming_call_sound)
    print("Call from ", a.get('LineIdentification'))

def ended_call(o):
    pass

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
        try:
            subprocess.call(["/usr/bin/sudo","/bin/ip","address","del", str(net_params.get("Address"))+"/"+str(net_params.get("Netmask")), "dev", str(net_params.get("Interface"))])
        except:
            print("Could not manually flush old ip")

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
    system.add_signal_receiver(incoming_call, signal_name="CallAdded", dbus_interface="org.ofono.VoiceCallManager")
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
