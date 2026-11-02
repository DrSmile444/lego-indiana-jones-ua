// Experimental resource overlay for the verified Steam x86 executable.
// Included after Log() and SupportedExecutable() in the DirectInput proxy.
#include <stdio.h>

#pragma pack(push, 1)
struct UapEntry { char path[256]; DWORD offset, size; BYTE sha256[32]; };
#pragma pack(pop)
static BYTE *uap_bytes;
static DWORD uap_size, uap_count;
static UapEntry *uap_entries;
typedef int (__cdecl *OpenResource)(const char *, int, void *, int);
typedef int (__cdecl *ExistsResource)(const char *);
typedef __int64 (__cdecl *SizeResource)(const char *);
typedef int (__cdecl *OpenMemory)(void *, int, int);
typedef int (__cdecl *ReadWholeResource)(const char *, void *, int);
typedef __int64 (__cdecl *HandleSize)(int);
static OpenResource original_open;
static ExistsResource original_exists;
static SizeResource original_size;
static OpenMemory open_memory;
static ReadWholeResource original_read_whole;
static BYTE *uap_game_base;
static HandleSize original_handle_size;
static bool uap_self_tested;
static const char *uap_pc_strings[38];
static void PatchUapDds(BYTE *bytes, DWORD size);

static UapEntry *FindUap(const char *path) {
    if (!path) return NULL;
    char normalized[256];
    size_t n = strlen(path);
    if (n >= sizeof(normalized)) return NULL;
    for (size_t i = 0; i <= n; ++i) {
        char c = path[i];
        normalized[i] = c == '\\' ? '/' : (c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c);
    }
    const char *relative = normalized;
    while (relative[0] == '.' && relative[1] == '/') relative += 2;
    for (DWORD i = 0; i < uap_count; ++i)
        if (!strcmp(relative, uap_entries[i].path)) return &uap_entries[i];
    return NULL;
}
static __int64 __cdecl UapHandleSize(int handle) {
    // Nu's memory-stream end pointer is inclusive, but its size function
    // returns end-start. Correct that off-by-one only for our own buffers.
    if (handle >= 0x400 && handle < 0x414) {
        BYTE *start = *(BYTE **)(uap_game_base + 0x6FAFF0 + (handle - 0x400) * 20);
        for (DWORD i = 0; i < uap_count; ++i)
            if (start == uap_bytes + uap_entries[i].offset) return uap_entries[i].size;
    }
    return original_handle_size(handle);
}
static void TestUapStreams() {
    typedef int (__cdecl *Read)(int, void *, int);
    typedef __int64 (__cdecl *Seek)(int, int, int, int);
    typedef void (__cdecl *Close)(int);
    Read read = (Read)(uap_game_base + 0x2B55A0);
    Seek seek = (Seek)(uap_game_base + 0x2B04C0);
    Close close = (Close)(uap_game_base + 0x2B38F0);
    DWORD passed = 0;
    for (DWORD i = 0; i < uap_count; ++i) {
        UapEntry &entry = uap_entries[i];
        BYTE *buffer = (BYTE *)HeapAlloc(GetProcessHeap(), 0, entry.size);
        if (!buffer) { Log("UAP SELFTEST FAIL: allocation."); return; }
        int handle = open_memory(uap_bytes + entry.offset, (int)entry.size, 0);
        bool ok = handle && UapHandleSize(handle) == entry.size;
        if (handle) {
            ok = ok && read(handle, buffer, (int)entry.size) == (int)entry.size &&
                memcmp(buffer, uap_bytes + entry.offset, entry.size) == 0;
            BYTE tail;
            ok = ok && read(handle, &tail, 1) == 0;
            ok = ok && seek(handle, (int)entry.size - 1, 0, 0) == entry.size - 1 &&
                read(handle, &tail, 1) == 1 && tail == uap_bytes[entry.offset + entry.size - 1];
            close(handle);
        }
        HeapFree(GetProcessHeap(), 0, buffer);
        // More than the 20-slot pool: closing must recycle the stream slot.
        for (int cycle = 0; cycle < 32 && ok; ++cycle) {
            handle = open_memory(uap_bytes + entry.offset, (int)entry.size, 0);
            if (!handle) { ok = false; break; }
            close(handle);
        }
        if (!ok) { Log("UAP SELFTEST FAIL: native read/size/seek/EOF/close."); return; }
        ++passed;
    }
    char message[180];
    sprintf_s(message, "UAP SELFTEST PASS: %lu resources; exact reads, sizes, last byte, EOF, seek and 32 reopen cycles each.", passed);
    Log(message);
}

static int __cdecl UapOpen(const char *path, int mode, void *archive, int flags) {
    UapEntry *entry = mode == 0 ? FindUap(path) : NULL;
    if (entry) {
        if (!uap_self_tested && !strcmp(entry->path, "STUFF/TEXT/ENGLISH.TXT")) {
            uap_self_tested = true;
            TestUapStreams();
        }
        int handle = open_memory(uap_bytes + entry->offset, (int)entry->size, 0);
        char message[380];
        sprintf_s(message, "UAP OPEN: %s size=%lu handle=%d", entry->path, entry->size, handle);
        Log(message);
        if (handle) return handle;
        Log("UAP ERROR: native memory stream slots exhausted; falling back.");
    }
    return original_open(path, mode, archive, flags);
}
static int __cdecl UapExists(const char *path) {
    if (FindUap(path)) return 1;
    return original_exists(path);
}
static __int64 __cdecl UapSize(const char *path) {
    UapEntry *entry = FindUap(path);
    return entry ? (__int64)entry->size : original_size(path);
}
static int __cdecl UapReadWhole(const char *path, void *destination, int capacity) {
    UapEntry *entry = FindUap(path);
    if (!entry) {
        int result = original_read_whole(path, destination, capacity);
        if (result > 0) PatchUapDds((BYTE *)destination, (DWORD)result);
        return result;
    }
    DWORD *error = (DWORD *)(uap_game_base + 0x7037EC);
    if (!destination || capacity < 0 || entry->size > (DWORD)capacity) {
        *error = 0xFFFFFFFF;
        Log("UAP READ ERROR: destination is too small.");
        return 0;
    }
    memcpy(destination, uap_bytes + entry->offset, entry->size);
    *error = 0;
    char message[380];
    sprintf_s(message, "UAP READ WHOLE: %s size=%lu", entry->path, entry->size);
    Log(message);
    return (int)entry->size;
}

// All stolen instructions are verified, complete, and position independent.
static void *MakeTrampoline(BYTE *site, SIZE_T count) {
    BYTE *buffer = (BYTE *)VirtualAlloc(NULL, count + 5, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!buffer) return NULL;
    memcpy(buffer, site, count);
    buffer[count] = 0xE9;
    *(DWORD *)(buffer + count + 1) = (DWORD)(ULONG_PTR)(site + count) - (DWORD)(ULONG_PTR)(buffer + count + 5);
    DWORD protection;
    if (!VirtualProtect(buffer, count + 5, PAGE_EXECUTE_READ, &protection)) {
        VirtualFree(buffer, 0, MEM_RELEASE);
        return NULL;
    }
    FlushInstructionCache(GetCurrentProcess(), buffer, count + 5);
    return buffer;
}
static bool SetJump(BYTE *site, void *function, SIZE_T count) {
    DWORD protection;
    if (!VirtualProtect(site, count, PAGE_EXECUTE_READWRITE, &protection)) return false;
    site[0] = 0xE9;
    *(DWORD *)(site + 1) = (DWORD)(ULONG_PTR)function - (DWORD)(ULONG_PTR)(site + 5);
    for (SIZE_T i = 5; i < count; ++i) site[i] = 0x90;
    DWORD ignored;
    VirtualProtect(site, count, protection, &ignored);
    FlushInstructionCache(GetCurrentProcess(), site, count);
    return true;
}
static bool LoadUap() {
    wchar_t path[MAX_PATH];
    if (!GetModuleFileNameW(self_module, path, MAX_PATH)) return false;
    wchar_t *name = wcsrchr(path, L'\\');
    if (!name || wcscpy_s(name + 1, MAX_PATH - (name + 1 - path), L"UKRAINIAN.uap")) return false;
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return false;
    DWORD size = GetFileSize(file, NULL), got = 0;
    if (size < 12 || size > 64 * 1024 * 1024) { CloseHandle(file); return false; }
    BYTE *bytes = (BYTE *)HeapAlloc(GetProcessHeap(), 0, size);
    bool read = bytes && ReadFile(file, bytes, size, &got, NULL) && got == size;
    CloseHandle(file);
    if (!read || memcmp(bytes, "UAP1\r\n\x1a\0", 8)) {
        if (bytes) HeapFree(GetProcessHeap(), 0, bytes);
        return false;
    }
    DWORD count = *(DWORD *)(bytes + 8);
    if (!count || count > 64 || 12 + count * sizeof(UapEntry) > size) {
        HeapFree(GetProcessHeap(), 0, bytes); return false;
    }
    UapEntry *entries = (UapEntry *)(bytes + 12);
    for (DWORD i = 0; i < count; ++i) {
        UapEntry &e = entries[i];
        if (!memchr(e.path, 0, 256) || !e.size || e.size > 32 * 1024 * 1024 ||
            e.offset < 12 + count * sizeof(UapEntry) || e.offset > size || e.size > size - e.offset) {
            HeapFree(GetProcessHeap(), 0, bytes); return false;
        }
        BCRYPT_ALG_HANDLE alg = NULL;
        BCRYPT_HASH_HANDLE hash = NULL;
        BYTE digest[32];
        bool valid = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) >= 0 &&
            BCryptCreateHash(alg, &hash, NULL, 0, NULL, 0, 0) >= 0 &&
            BCryptHashData(hash, bytes + e.offset, e.size, 0) >= 0 &&
            BCryptFinishHash(hash, digest, sizeof(digest), 0) >= 0 &&
            memcmp(digest, e.sha256, sizeof(digest)) == 0;
        if (hash) BCryptDestroyHash(hash);
        if (alg) BCryptCloseAlgorithmProvider(alg, 0);
        if (!valid) { HeapFree(GetProcessHeap(), 0, bytes); return false; }
    }
    UapEntry *pc = NULL;
    for (DWORD i = 0; i < count; ++i) {
        if (!strcmp(entries[i].path, "UKRAINIAN/PC_MENU.UTF8")) pc = &entries[i];
        for (DWORD j = 0; j < i; ++j) {
            if (!strcmp(entries[i].path, entries[j].path)) {
                HeapFree(GetProcessHeap(), 0, bytes); return false;
            }
        }
    }
    if (!pc) { HeapFree(GetProcessHeap(), 0, bytes); return false; }
    const char *cursor = (const char *)(bytes + pc->offset);
    const char *end = cursor + pc->size;
    for (int i = 0; i < 38; ++i) {
        const char *zero = (const char *)memchr(cursor, 0, end - cursor);
        if (!zero || zero == cursor) { HeapFree(GetProcessHeap(), 0, bytes); return false; }
        uap_pc_strings[i] = cursor;
        cursor = zero + 1;
    }
    if (cursor != end) { HeapFree(GetProcessHeap(), 0, bytes); return false; }
    uap_bytes = bytes; uap_size = size; uap_count = count; uap_entries = entries;
    return true;
}
#include "textures.h"
#include "custom_names.h"

static bool InitializeUap(BYTE *base) {
    const BYTE expect_open[] = {0x81, 0xEC, 0x04, 0x01, 0x00, 0x00};
    const BYTE expect_exists[] = {0x57, 0x8B, 0x7C, 0x24, 0x08};
    const BYTE expect_size[] = {0x51, 0xA1, 0xD8, 0x37, 0xB0, 0x00};
    const BYTE expect_whole[] = {0xA1, 0xD0, 0x37, 0xB0, 0x00};
    const BYTE expect_hsize[] = {0x8B, 0x44, 0x24, 0x04, 0x3D, 0x00, 0x10, 0x00, 0x00};
    BYTE *op = base + 0x2B44F0, *ex = base + 0x2B46D0, *sz = base + 0x2B4750;
    BYTE *whole = base + 0x2B7440;
    BYTE *hsize = base + 0x2B0250;
    if (memcmp(op, expect_open, 6) || memcmp(ex, expect_exists, 5) || memcmp(sz, expect_size, 6) ||
        memcmp(whole, expect_whole, 5) || memcmp(hsize, expect_hsize, 9)) {
        Log("UAP SKIP: unexpected resource function bytes."); return false;
    }
    if (!LoadUap()) { Log("UAP SKIP: missing, invalid or corrupt UKRAINIAN.uap."); return false; }
    original_open = (OpenResource)MakeTrampoline(op, 6);
    original_exists = (ExistsResource)MakeTrampoline(ex, 5);
    original_size = (SizeResource)MakeTrampoline(sz, 6);
    original_read_whole = (ReadWholeResource)MakeTrampoline(whole, 5);
    original_handle_size = (HandleSize)MakeTrampoline(hsize, 9);
    uap_game_base = base;
    open_memory = (OpenMemory)(base + 0x2AA040);
    if (!original_open || !original_exists || !original_size || !original_read_whole || !original_handle_size) {
        Log("UAP SKIP: cannot allocate trampolines."); return false;
    }
    struct Hook { BYTE *site; void *replacement; void *original; SIZE_T size; };
    Hook hooks[] = {
        {op, (void *)&UapOpen, (void *)original_open, 6},
        {ex, (void *)&UapExists, (void *)original_exists, 5},
        {sz, (void *)&UapSize, (void *)original_size, 6},
        {whole, (void *)&UapReadWhole, (void *)original_read_whole, 5},
        {hsize, (void *)&UapHandleSize, (void *)original_handle_size, 9}
    };
    for (int i = 0; i < 5; ++i) {
        if (SetJump(hooks[i].site, hooks[i].replacement, hooks[i].size)) continue;
        for (int j = i - 1; j >= 0; --j) {
            DWORD protection, ignored;
            if (VirtualProtect(hooks[j].site, hooks[j].size, PAGE_EXECUTE_READWRITE, &protection)) {
                memcpy(hooks[j].site, hooks[j].original, hooks[j].size);
                VirtualProtect(hooks[j].site, hooks[j].size, protection, &ignored);
                FlushInstructionCache(GetCurrentProcess(), hooks[j].site, hooks[j].size);
            }
        }
        Log("UAP ERROR: hook installation failed; previous hooks restored."); return false;
    }
    Log("UAP READY: UKRAINIAN.uap verified; open/existence/size/whole-file hooks installed.");
    InitializeUapTextures(base);
    InitializeCustomNameUtf8(base);
    InitializeDefaultCustomNames(base);
    return true;
}
