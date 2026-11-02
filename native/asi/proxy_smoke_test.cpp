// Real DirectInput integration in a deliberately unsupported host executable.
#define WIN32_LEAN_AND_MEAN
#define DIRECTINPUT_VERSION 0x0800
#include <windows.h>
#include <dinput.h>
#include <stdio.h>

int wmain(int argc, wchar_t **argv) {
    if (argc != 2) return 2;
    HMODULE proxy = LoadLibraryW(argv[1]);
    if (!proxy) { printf("LoadLibrary failed: %lu\n", GetLastError()); return 3; }
    typedef HRESULT (WINAPI *Create)(HINSTANCE, DWORD, REFIID, LPVOID *, LPUNKNOWN);
    Create create = (Create)GetProcAddress(proxy, "DirectInput8Create");
    if (!create) return 4;
    IDirectInput8W *input = NULL;
    HRESULT result = create(GetModuleHandleW(NULL), DIRECTINPUT_VERSION, IID_IDirectInput8W,
                            (LPVOID *)&input, NULL);
    printf("DirectInput8Create HRESULT: 0x%08lx\n", (unsigned long)result);
    if (FAILED(result) || !input) return 5;
    input->Release();
    typedef HRESULT (WINAPI *CanUnload)();
    CanUnload can_unload = (CanUnload)GetProcAddress(proxy, "DllCanUnloadNow");
    if (!can_unload || can_unload() != S_FALSE) return 6;
    FreeLibrary(proxy);
    puts("PASS: system DirectInput object created and released; proxy declines COM unload.");
    return 0;
}
