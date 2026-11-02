// Test-only ASI, never shipped. Demonstrates an independent second plugin.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>
static HMODULE self;
static LONG started;
extern "C" void InitializeASI() {
    if (InterlockedCompareExchange(&started, 1, 0)) return;
    wchar_t path[MAX_PATH];
    if (!GetModuleFileNameW(self, path, MAX_PATH)) return;
    wchar_t *name = wcsrchr(path, L'\\');
    if (!name || wcscpy_s(name + 1, MAX_PATH - (name + 1 - path), L"ASI_COEXISTENCE_TEST.log")) return;
    const char *message = "PASS: independent second ASI initialized.\r\n";
    HMODULE localization = GetModuleHandleW(L"UKRAINIAN.asi");
    if (localization) {
        typedef void (__cdecl *Init)();
        Init initialize = (Init)GetProcAddress(localization, "InitializeASI");
        if (initialize) {
            initialize();
            initialize();
            message = "PASS: independent second ASI initialized; localization initializer called twice again.\r\n";
        }
    }
    HANDLE file = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file != INVALID_HANDLE_VALUE) {
        DWORD written;
        WriteFile(file, message, (DWORD)strlen(message), &written, NULL);
        CloseHandle(file);
    }
}
BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) { self = module; DisableThreadLibraryCalls(module); }
    return TRUE;
}
