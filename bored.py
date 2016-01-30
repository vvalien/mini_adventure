import sys
import argparse
import logging
from impacket.examples import logger
from impacket.dcerpc.v5.rpcrt import *
from impacket.dcerpc.v5 import transport, dcomrt
from impacket import ntlm
from impacket.uuid import string_to_bin, uuidtup_to_bin
# Hopefully for something awesome, if not I learned how to make rpc connections
# The other version works perfectly on 8.1 ... so atleast i have that


def first_msg_transfer(first_auth_packet, rtransport, iface_uuid):
	transfer_syntax = ('8a885d04-1ceb-11c9-9fe8-08002b104860', '2.0')
	ctx = 0
	callid = 1
	
	bind = MSRPCBind()
	# The true one :)
	item = CtxItem()
	item['AbstractSyntax'] = iface_uuid # worry about this later not now
	item['TransferSyntax'] = uuidtup_to_bin(transfer_syntax) # 32bit tcp 135
	item['ContextID'] = ctx
	item['TransItems'] = 1
	bind.addCtxItem(item)
	
	packet = MSRPCHeader()
	packet['type'] = MSRPC_BIND
	packet['pduData'] = str(bind)
	packet['call_id'] = callid
	
	# second blank is domain 
	# sign is not set on webdav fyi
	# to make a valid connection we would do this
	#auth = ntlm.getNTLMSSPType1('', '', signingRequired = True, use_ntlmv2 = False)
	sec_trailer = SEC_TRAILER()
	sec_trailer['auth_type']   = RPC_C_AUTHN_WINNT
	sec_trailer['auth_level']  = RPC_C_AUTHN_LEVEL_CONNECT # will need changed to pkt
	sec_trailer['auth_ctx_id'] = ctx + 79231 
	
	pad = (4 - (len(packet.get_packet()) % 4)) % 4
	if pad != 0:
		packet['pduData'] += '\xFF'*pad
		sec_trailer['auth_pad_len']=pad
	
	packet['sec_trailer'] = sec_trailer
	# We insert that shit here!!!!!!!!!!
	packet['auth_data'] = str(first_auth_packet)
	
	### CONNECT TO THAT BITCH
	rtransport.connect()
	### SEND THAT BITCH
	rtransport.send(packet.get_packet())
	### RECV THAT BITCH
	s = rtransport.recv()
	# Move it into usable content
	resp = MSRPCHeader(s)
	# Rip out the auth data
	second_response = resp['auth_data']
	#for info
	#resp.dump()
	return second_response, rtransport


def third_msg_transfer(third_auth_packet, rtransport):
	sec_trailer = SEC_TRAILER()
	sec_trailer['auth_type'] = RPC_C_AUTHN_WINNT
	sec_trailer['auth_level'] = RPC_C_AUTHN_LEVEL_CONNECT # will need changed to pkt
	sec_trailer['auth_ctx_id'] = ctx + 79231 
	
	auth3 = MSRPCHeader()
	auth3['type'] = MSRPC_AUTH3
	auth3['pduData'] = '    '
	auth3['sec_trailer'] = sec_trailer
	auth3['auth_data'] = str(third_auth_packet)
	auth3['call_id'] = callid
	
	### SEND THAT BITCH BACK
	rtransport.send(auth3.get_packet(), forceWriteAndx = 1)
	




machine = '192.168.1.15'
# setup the connection to RPC
# random iface_uuid
iface_uuid = generate() + stringver_to_bin('2.0')
stringBinding = r'ncacn_ip_tcp:%s' % machine
rtransport = transport.DCERPCTransportFactory(stringBinding)



second_response, rtransport = first_msg_transfer(first_auth_packet, rtransport, iface_uuid)
third_msg_transfer(third_auth_packet, rtransport)
