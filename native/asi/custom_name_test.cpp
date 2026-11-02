#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
static BYTE *uap_game_base;
static void Log(const char *) {}
#include "custom_names.h"
#include "practice_cutscenes.h"
static char rendered[128];
static const char *test_full_name;
static const char *__cdecl CopyFullName(int, void *, char *destination, int) {
    memcpy(destination, test_full_name, strlen(test_full_name) + 1);
    return destination;
}
static const char fallback[] = "X";
static void __cdecl CaptureGlyph(const char *text) { strcpy_s(rendered, text); }
static __declspec(naked) void InvokeDraw(int, int) {
    __asm {
        push edi
        push esi
        mov edi, [esp + 12]
        mov esi, [esp + 16]
        push offset fallback
        call SafeEditorNameDraw
        add esp, 4
        pop esi
        pop edi
        ret
    }
}
int main() {
    uap_game_base = (BYTE *)VirtualAlloc(NULL, 0x510000, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!uap_game_base) return 1;
    const BYTE format_call[] = {0xE8,0x28,0xDE,0x11,0x00};
    BYTE *format_site = uap_game_base + 0x1F4BB2;
    memcpy(format_site, format_call, 5);
    if (!InitializeDefaultCustomNames(uap_game_base)) return 30;
    typedef int (__cdecl *FormatName)(char *, const char *, const char *, int);
    FormatName format = (FormatName)(format_site + 5 + *(LONG *)(format_site + 1));
    for (int number = 1; number <= 2; ++number) {
        struct { char name[32]; char canary; } result = {{0}, 'Z'};
        const char *expected = number == 1 ? u8"Форелька" : u8"Льоля";
        if (format(result.name, "%s %i", "Stranger", number) != (int)strlen(expected) ||
            strcmp(result.name, expected) || result.canary != 'Z') return 31;
    }
    if (InitializeDefaultCustomNames(uap_game_base)) return 32;
    puts("PASS: native initialization call uses distinct UTF-8 names without numbers.");
    BYTE *predicate = uap_game_base + 0x2A0250;
    const BYTE predicate_bytes[] = {0x8B,0x44,0x24,0x04,0x8B,0x80,0x88,0,0,0,0xC1,0xE0,0x13,0xC1,0xF8,0x1F,0xC3};
    memcpy(predicate, predicate_bytes, sizeof(predicate_bytes));
    DWORD old;
    VirtualProtect(predicate, sizeof(predicate_bytes), PAGE_EXECUTE_READWRITE, &old);
    typedef int (__cdecl *Complete)(void *);
    Complete complete = (Complete)predicate;
    DWORD scene[36] = {};
    if (complete(scene) != 0) return 20;
    if (!ApplyPracticeCutscenes(uap_game_base) || complete(scene) == 0) return 21;
    scene[0x88 / 4] = 0xFFFFFFFF;
    if (complete(scene) == 0 || ApplyPracticeCutscenes(uap_game_base)) return 22;
    puts("PASS: practice completion predicate; original, patched and mismatched code.");
    BYTE records[0x70] = {};
    *(BYTE **)(uap_game_base + 0x509C80) = records;
    const BYTE call[] = {0xE8, 0x0C, 0xE3, 0x04, 0x00};
    memcpy(uap_game_base + 0x24C6AF, call, sizeof(call));
    const BYTE get_call[] = {0xE8, 0x8C, 0x52, 0xF6, 0xFF};
    const BYTE draw_call[] = {0xE8, 0x4E, 0xE2, 0x04, 0x00};
    memcpy(uap_game_base + 0x24C6FF, get_call, 5);
    memcpy(uap_game_base + 0x24C76D, draw_call, 5);
    if (!InitializeCustomNameUtf8(uap_game_base)) return 2;
    if (uap_game_base[0x24C6AF] != 0xE8) return 3;
    native_editor_draw = (void *)&CaptureGlyph;
    native_editor_name_get = &CopyFullName;
    const char *names[] = {u8"Форелька 1", u8"Форелька 2", u8"Незнайомець 1"};
    for (const char *name : names) {
        test_full_name = name;
        char native_stack[64];
        memset(native_stack, 'Z', sizeof(native_stack));
        CopyFullName(0, NULL, native_stack, 0);
        // Reproduce the native 16-byte buffer overwrite before applying fix.
        if (native_stack[16] == 'Z') return 8;
        memset(native_stack, 'Z', sizeof(native_stack));
        SafeEditorNameGet(0, NULL, native_stack, 0);
        for (char value : native_stack) if (value != 'Z') return 9;
        typedef void (__cdecl *Draw)(const char *);
        ((Draw)&SafeEditorFullNameDraw)(native_stack);
        if (strcmp(rendered, name)) return 10;
    }
    for (int slot = 0; slot < 2; ++slot) {
        for (const char *name : names) {
            memset(records, 0, sizeof(records));
            strcpy_s((char *)records + slot * 0x38 + 0x14, 32, name);
            std::string full;
            for (int index = 0; index < 15; ++index) {
                InvokeDraw(slot, index);
                full += rendered;
            }
            while (!full.empty() && full.back() == ' ') full.pop_back();
            if (full != name) return 4;
        }
    }
    memset(records, 0, sizeof(records));
    strcpy_s((char *)records + 0x14, 32, "Stranger 1");
    InvokeDraw(0, 0);
    if (strcmp(rendered, fallback)) return 5;
    const unsigned char broken[] = {0xD0, 0};
    struct { char text[5]; char canary; } output = {{0}, 'Z'};
    if (!EditorNameGlyph(broken, sizeof(broken), 0, output.text) ||
        strcmp(output.text, "?") || output.canary != 'Z') return 6;
    const unsigned char boundary[] = {0xD0};
    if (!EditorNameGlyph(boundary, sizeof(boundary), 0, output.text) || strcmp(output.text, "?")) return 7;
    VirtualFree(uap_game_base, 0, MEM_RELEASE);
    puts("PASS: reproduced 16-byte native overflow; protected full-name get/draw; both slots and UTF-8 cells.");
    return 0;
}
