#include "custom_name_utf8.h"
static int __cdecl FormatDefaultCustomName(char *destination, const char *, const char *, int number) {
    const char *name = number == 1 ? u8"Форелька" : u8"Льоля";
    strcpy_s(destination, 32, name);
    return (int)strlen(name);
}
static bool InitializeDefaultCustomNames(BYTE *base) {
    BYTE *site = base + 0x1F4BB2;
    const BYTE expected[] = {0xE8,0x28,0xDE,0x11,0x00};
    if (memcmp(site, expected, 5)) {
        Log("CUSTOM DEFAULT NAMES SKIP: unexpected initialization call."); return false;
    }
    DWORD protection, ignored;
    if (!VirtualProtect(site, 5, PAGE_EXECUTE_READWRITE, &protection)) return false;
    *(DWORD *)(site + 1) = (DWORD)(ULONG_PTR)&FormatDefaultCustomName - (DWORD)(ULONG_PTR)(site + 5);
    VirtualProtect(site, 5, protection, &ignored);
    FlushInstructionCache(GetCurrentProcess(), site, 5);
    Log("CUSTOM DEFAULT NAMES READY: distinct names, no numeric suffixes.");
    return true;
}
static void *native_editor_draw;
typedef const char *(__cdecl *EditorNameGet)(int, void *, char *, int);
static EditorNameGet native_editor_name_get;
static char editor_full_name[1024];
static const char *editor_full_name_text = editor_full_name;
static const char *__cdecl SafeEditorNameGet(int id, void *character, char *, int flags) {
    // The native caller supplies only 16 bytes, while the saved field allows
    // 32 bytes and UTF-8 defaults exceed 16. Never write into that stack buffer.
    editor_full_name[0] = 0;
    editor_full_name_text = native_editor_name_get(id, character, editor_full_name, flags);
    if (!editor_full_name_text) editor_full_name_text = "";
    return editor_full_name_text;
}
static __declspec(naked) void SafeEditorFullNameDraw() {
    __asm {
        mov eax, dword ptr [editor_full_name_text]
        mov [esp + 4], eax
        jmp dword ptr [native_editor_draw]
    }
}
static const char *__cdecl SelectEditorNameGlyph(const char *fallback, int slot, int index) {
    static char glyph[5];
    if (slot < 0 || slot > 1 || index < 0 || index >= 15) return fallback;
    BYTE *records = *(BYTE **)(uap_game_base + 0x509C80);
    if (!records) return fallback;
    const unsigned char *name = records + slot * 0x38 + 0x14;
    return EditorNameGlyph(name, 32, (unsigned)index, glyph) ? glyph : fallback;
}
static __declspec(naked) void SafeEditorNameDraw() {
    __asm {
        pushfd
        pushad
        mov eax, [esp + 40]
        push esi
        push edi
        push eax
        call SelectEditorNameGlyph
        add esp, 12
        mov [esp + 40], eax
        popad
        popfd
        jmp dword ptr [native_editor_draw]
    }
}
static bool InitializeCustomNameUtf8(BYTE *base) {
    struct Call { DWORD offset; BYTE expected[5]; void *replacement; };
    Call calls[] = {
        {0x24C6AF, {0xE8, 0x0C, 0xE3, 0x04, 0x00}, (void *)&SafeEditorNameDraw},
        {0x24C6FF, {0xE8, 0x8C, 0x52, 0xF6, 0xFF}, (void *)&SafeEditorNameGet},
        {0x24C76D, {0xE8, 0x4E, 0xE2, 0x04, 0x00}, (void *)&SafeEditorFullNameDraw}
    };
    for (const Call &call : calls) {
        if (memcmp(base + call.offset, call.expected, 5)) {
            Log("CUSTOM NAME UTF8 SKIP: unexpected editor calls."); return false;
        }
    }
    native_editor_draw = base + 0x29A9C0;
    native_editor_name_get = (EditorNameGet)(base + 0x1B1990);
    DWORD protection, ignored;
    // All three calls live in the same verified executable page.
    BYTE *page = base + 0x24C000;
    if (!VirtualProtect(page, 0x1000, PAGE_EXECUTE_READWRITE, &protection)) return false;
    for (const Call &call : calls) {
        BYTE *site = base + call.offset;
        *(DWORD *)(site + 1) = (DWORD)(ULONG_PTR)call.replacement - (DWORD)(ULONG_PTR)(site + 5);
    }
    VirtualProtect(page, 0x1000, protection, &ignored);
    FlushInstructionCache(GetCurrentProcess(), page, 0x1000);
    Log("CUSTOM NAME UTF8 READY v2: full-name stack buffer protected; complete name cells.");
    return true;
}
