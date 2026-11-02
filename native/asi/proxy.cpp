// x86 proxy: forward DirectInput unchanged, replace only the English PC tables.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <unknwn.h>
#include <string.h>
#include <stdio.h>
#include "pc_strings.h"
#include "ua_version.h"

static_assert(sizeof(void *) == 4, "The game requires a 32-bit DLL");
static HMODULE self_module;
#ifndef UAP_ASI
static HMODULE system_module;
static FARPROC real_exports[6];
#endif
static INIT_ONCE once = INIT_ONCE_STATIC_INIT;

static void Log(const char *message) {
    wchar_t path[MAX_PATH];
    DWORD length = GetModuleFileNameW(self_module, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return;
    wchar_t *name = wcsrchr(path, L'\\');
    if (!name) return;
    if (wcscpy_s(name + 1, MAX_PATH - (name + 1 - path), L"legoindy-ua-pc.log")) return;
    HANDLE file = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                              NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return;
    DWORD written;
    WriteFile(file, message, (DWORD)strlen(message), &written, NULL);
    WriteFile(file, "\r\n", 2, &written, NULL);
    CloseHandle(file);
}

static bool SupportedExecutable() {
    wchar_t path[MAX_PATH];
    DWORD length = GetModuleFileNameW(NULL, path, MAX_PATH);
    if (!length || length >= MAX_PATH) return false;
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return false;
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    PUCHAR object = NULL;
    DWORD object_size = 0, result_size = 0, received = 0;
    unsigned char digest[32], buffer[65536];
    bool ok = false;
    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0) goto done;
    if (BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&object_size,
                          sizeof(object_size), &result_size, 0) < 0) goto done;
    object = (PUCHAR)HeapAlloc(GetProcessHeap(), 0, object_size);
    if (!object) goto done;
    if (BCryptCreateHash(algorithm, &hash, object, object_size, NULL, 0, 0) < 0) goto done;
    for (;;) {
        if (!ReadFile(file, buffer, sizeof(buffer), &received, NULL)) goto done;
        if (!received) break;
        if (BCryptHashData(hash, buffer, received, 0) < 0) goto done;
    }
    if (BCryptFinishHash(hash, digest, sizeof(digest), 0) < 0) goto done;
    ok = memcmp(digest, expected_sha256, sizeof(digest)) == 0;
done:
    if (hash) BCryptDestroyHash(hash);
    if (object) HeapFree(GetProcessHeap(), 0, object);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    CloseHandle(file);
    return ok;
}

static bool PcTableAccessible(void *address, SIZE_T size) {
    MEMORY_BASIC_INFORMATION info;
    if (!VirtualQuery(address, &info, sizeof(info)) || info.State != MEM_COMMIT) return false;
#ifdef UAP_ASI
    // Steam exposes these initialized data pages as copy-on-write at ASI startup.
    // They are writable: the OS gives this process a private page on first store.
    if (info.Protect != PAGE_READWRITE && info.Protect != PAGE_EXECUTE_READWRITE &&
        info.Protect != PAGE_WRITECOPY && info.Protect != PAGE_EXECUTE_WRITECOPY) return false;
#else
    if (info.Protect != PAGE_READWRITE && info.Protect != PAGE_EXECUTE_READWRITE) return false;
#endif
    return (BYTE *)address >= info.BaseAddress &&
           (BYTE *)address + size <= (BYTE *)info.BaseAddress + info.RegionSize;
}

struct Entry { DWORD id; const char *text; };

#ifdef UAP_EXPERIMENT
#include "overlay.h"
#endif

#ifdef FONT_UPSCALE_EXPERIMENT
static int __cdecl LoadFontTexture(BYTE *texture) {
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
    typedef int (__cdecl *Load)(BYTE *);
    int index = ((Load)(base + 0x2FE2B0))(texture);
    // Only this call site loads font atlases. GPU texture stays 2048;
    // CPU font geometry and UV calculations retain the original units.
    if (index > 0 && *(DWORD *)texture == 2048 && *(DWORD *)(texture + 4) == 2048) {
        *(DWORD *)texture = 1024;
        *(DWORD *)(texture + 4) = 1024;
        Log("OK: 2048 font GPU atlas uses original 1024 logical coordinates.");
    }
    return index;
}
#endif

static void TranslatePcTables() {
    if (!SupportedExecutable()) {
        Log("SKIP: unsupported executable SHA-256; game memory unchanged.");
        return;
    }
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
#ifdef UAP_EXPERIMENT
    if (!InitializeUap(base)) return;
    const char *const *translated = uap_pc_strings;
#else
    const char *const *translated = ukrainian_text;
#endif
#ifdef FONT_UPSCALE_EXPERIMENT
    // The font loader passes a fixed 2 MiB DDS size to D3DX. A 2048 BC3
    // atlas with all mip levels needs 5,592,560 bytes. Disk EXE is unchanged.
    BYTE *font_size_instruction = base + 0x303B3A;
    const BYTE expected[] = {0xC7, 0x40, 0x78, 0x00, 0x00, 0x20, 0x00};
    BYTE *font_load_call = base + 0x303B41;
    const BYTE expected_call[] = {0xE8, 0x6A, 0xA7, 0xFF, 0xFF};
    if (memcmp(font_size_instruction, expected, sizeof(expected)) != 0 ||
        memcmp(font_load_call, expected_call, sizeof(expected_call)) != 0) {
        Log("SKIP: unexpected font DDS size instruction.");
        return;
    }
    DWORD old_protection;
    const SIZE_T patch_size = sizeof(expected) + sizeof(expected_call);
    if (!VirtualProtect(font_size_instruction, patch_size, PAGE_EXECUTE_READWRITE, &old_protection)) {
        Log("SKIP: cannot update font DDS size instruction.");
        return;
    }
    const DWORD dds_size = 5592560;
    memcpy(font_size_instruction + 3, &dds_size, sizeof(dds_size));
    const DWORD relative_hook = (DWORD)(ULONG_PTR)&LoadFontTexture - (DWORD)(ULONG_PTR)(font_load_call + 5);
    memcpy(font_load_call + 1, &relative_hook, sizeof(relative_hook));
    DWORD ignored;
    VirtualProtect(font_size_instruction, patch_size, old_protection, &ignored);
    FlushInstructionCache(GetCurrentProcess(), font_size_instruction, patch_size);
    Log("OK: experimental font DDS size increased to 5592560 bytes.");
#endif
    Entry *tables[2] = {(Entry *)(base + 0x521D10), (Entry *)(base + 0x521E48)};
    const char **active = (const char **)(base + 0x5D0C30);
    const DWORD *initialized = (const DWORD *)(base + 0x5D0CC8);
    // Validate every table entry before enabling writes or changing pointers.
    for (int t = 0; t < 2; ++t) {
        if (!PcTableAccessible(tables[t], sizeof(Entry) * 39)) {
            Log("SKIP: PC source table has unexpected memory protection.");
            return;
        }
        bool seen[38] = {};
        for (int i = 0; i < 38; ++i) {
            const Entry &entry = tables[t][i];
            if (entry.id >= 38 || seen[entry.id] ||
                entry.text != (const char *)(base + original_rva[entry.id]) ||
                strcmp(entry.text, original_text[entry.id]) != 0) {
                Log("SKIP: unexpected PC table layout or another text modification.");
                return;
            }
            seen[entry.id] = true;
        }
        if (tables[t][38].id != 38 || tables[t][38].text != NULL) {
            Log("SKIP: unexpected PC table terminator.");
            return;
        }
    }
    if (!PcTableAccessible(active, sizeof(void *) * 38 + sizeof(DWORD))) {
        Log("SKIP: active PC table has unexpected memory protection.");
        return;
    }
    bool active_english = *initialized == 1;
    for (int i = 0; i < 38 && active_english; ++i)
        active_english = active[i] == (const char *)(base + original_rva[i]);
    for (int t = 0; t < 2; ++t)
        for (int i = 0; i < 38; ++i)
            InterlockedExchangePointer((PVOID volatile *)&tables[t][i].text,
                                        (PVOID)translated[tables[t][i].id]);
    if (active_english)
        for (int i = 0; i < 38; ++i)
            InterlockedExchangePointer((PVOID volatile *)&active[i], (PVOID)translated[i]);
    Log(active_english ? "OK: 76 English source pointers and 38 active pointers translated."
                       : "OK: 76 English source pointers translated before English PC initialization.");
}

static BOOL CALLBACK Initialize(PINIT_ONCE, PVOID, PVOID *) {
    // Called by exported functions, outside DllMain's loader lock.
#ifdef UAP_ASI
    // Game tables and detours retain pointers into this module for process life.
    HMODULE pinned;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                           (LPCWSTR)&Initialize, &pinned)) {
        Log("ASI ERROR: cannot pin localization module.");
        return TRUE;
    }
    Log("ASI INIT: v" UA_VERSION "; InitializeASI; once per process.");
#else
    wchar_t path[MAX_PATH];
    UINT length = GetSystemDirectoryW(path, MAX_PATH);
    if (!length || length >= MAX_PATH || wcscat_s(path, L"\\dinput8.dll")) {
        Log("ERROR: cannot resolve system DirectInput path.");
        return TRUE;
    }
    system_module = LoadLibraryExW(path, NULL, LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!system_module) {
        Log("ERROR: cannot load system DirectInput.");
        return TRUE;
    }
    const char *names[6] = {"DirectInput8Create", "DllCanUnloadNow", "DllGetClassObject",
                           "DllRegisterServer", "DllUnregisterServer", "GetdfDIJoystick"};
    for (int i = 0; i < 6; ++i) {
        real_exports[i] = GetProcAddress(system_module, names[i]);
        if (!real_exports[i]) {
            Log("ERROR: missing system DirectInput export.");
            return TRUE;
        }
    }
#endif
    TranslatePcTables();
    return TRUE;
}

#ifdef UAP_ASI
extern "C" void InitializeASI() {
    InitOnceExecuteOnce(&once, Initialize, NULL, NULL);
}
#else
static FARPROC Resolve(int index) {
    InitOnceExecuteOnce(&once, Initialize, NULL, NULL);
    return real_exports[index];
}

extern "C" HRESULT WINAPI ProxyDirectInput8Create(HINSTANCE instance, DWORD version,
    REFIID iid, LPVOID *output, LPUNKNOWN outer) {
    typedef HRESULT (WINAPI *Function)(HINSTANCE, DWORD, REFIID, LPVOID *, LPUNKNOWN);
    Function function = (Function)Resolve(0);
    return function ? function(instance, version, iid, output, outer) : E_FAIL;
}
extern "C" HRESULT WINAPI ProxyDllCanUnloadNow() {
    // Source tables retain pointers into this DLL for the process lifetime.
    return S_FALSE;
}
extern "C" HRESULT WINAPI ProxyDllGetClassObject(REFCLSID clsid, REFIID iid, LPVOID *output) {
    typedef HRESULT (WINAPI *Function)(REFCLSID, REFIID, LPVOID *);
    Function function = (Function)Resolve(2);
    return function ? function(clsid, iid, output) : E_FAIL;
}
extern "C" HRESULT WINAPI ProxyDllRegisterServer() {
    typedef HRESULT (WINAPI *Function)();
    Function function = (Function)Resolve(3);
    return function ? function() : E_FAIL;
}
extern "C" HRESULT WINAPI ProxyDllUnregisterServer() {
    typedef HRESULT (WINAPI *Function)();
    Function function = (Function)Resolve(4);
    return function ? function() : E_FAIL;
}
extern "C" const void *WINAPI ProxyGetdfDIJoystick() {
    typedef const void *(WINAPI *Function)();
    Function function = (Function)Resolve(5);
    return function ? function() : NULL;
}
#endif
BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        self_module = module;
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
