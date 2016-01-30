// None of this is my code but I thought it was nifty to just combine the 2
// Could be useful in the future or for reference later on.
// Use with visual studia console app c++
// Check WebClient with services.msc

#include "stdafx.h"
#include "evntprov.h"


bool StartWebClient()
{
	// The uuid for WebClient = 22b6d684-fa63-4578-87c9-effcbe6643c7
	// Found with sc qtriggerinfo WebClient
	const GUID _MS_Windows_WebClntLookupServiceTrigger_Provider =
	{ 0x22B6D684, 0xFA63, 0x4578,
	{ 0x87, 0xC9, 0xEF, 0xFC, 0xBE, 0x66, 0x43, 0xC7 } };

	REGHANDLE Handle;

	bool sucess = false;

	if (EventRegister(&_MS_Windows_WebClntLookupServiceTrigger_Provider,
		nullptr, nullptr, &Handle) == ERROR_SUCCESS)
	{
		EVENT_DESCRIPTOR desc;
		EventDescCreate(&desc, 1, 0, 0, 4, 0, 0, 0);
		sucess = EventWrite(Handle, &desc, 0, nullptr) == ERROR_SUCCESS;
		EventUnregister(Handle);
	}
	return sucess;
}


bool CheckWebClient()
{
	bool ret = false;
	SC_HANDLE sc = OpenSCManager(NULL, SERVICES_ACTIVE_DATABASE, SC_MANAGER_CONNECT);
	if (sc)
	{
		SC_HANDLE service = OpenService(sc, L"webclient", SERVICE_QUERY_STATUS);
		if (service)
		{
			SERVICE_STATUS status;
			if (QueryServiceStatus(service, &status))
			{
				ret = status.dwCurrentState == SERVICE_RUNNING;
			}
			CloseServiceHandle(service);
		}
		else
		{
			printf("Error opening webclient service: %d\n", GetLastError());
		}

		CloseServiceHandle(sc);
	}
	else
	{
		printf("Error opening service manager %d\n", GetLastError());
	}

	return ret;
}

int _tmain()
{
	if (!CheckWebClient())
	{
		printf("Starting the webclient service via uuid!\n");
		StartWebClient();
	}
	else
	{
		printf("The Webclient service is already running!\n");
	}
}
