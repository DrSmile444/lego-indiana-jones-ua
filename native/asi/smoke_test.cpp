#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
int wmain(int argc, wchar_t **argv) {
    if (argc != 2) return 2;
    HMODULE plugin = LoadLibraryW(argv[1]);
    if (!plugin) return 3;
    typedef void (__cdecl *InitializePlugin)();
    InitializePlugin initialize = (InitializePlugin)GetProcAddress(plugin, "InitializeASI");
    if (!initialize || GetProcAddress(plugin, "DirectInput8Create")) return 4;
    initialize();
    initialize();
    FreeLibrary(plugin);
    puts("PASS: ASI loaded, undecorated initializer callable twice, no DirectInput proxy exports.");
    return 0;
}
