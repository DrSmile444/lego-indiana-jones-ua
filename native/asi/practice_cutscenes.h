// Optional practice patch described by WiiSuper's LIJ1 guide:
// https://www.youtube.com/watch?v=ejuA7HDLdzw
// Apply to the verified, decrypted code in memory; never edit the game EXE.
static bool ApplyPracticeCutscenes(BYTE *base) {
    BYTE *site = base + 0x2A0250;
    const BYTE expected[] = {0x8B,0x44,0x24,0x04,0x8B,0x80,0x88,0,0,0,0xC1,0xE0,0x13,0xC1,0xF8,0x1F,0xC3};
    if (memcmp(site, expected, sizeof(expected))) {
        Log("PRACTICE CUTSCENES SKIP: unexpected completion predicate."); return false;
    }
    DWORD protection, ignored;
    if (!VirtualProtect(site, sizeof(expected), PAGE_EXECUTE_READWRITE, &protection)) return false;
    const BYTE replacement[] = {0x83,0xF0,0x01};
    memcpy(site + 13, replacement, sizeof(replacement));
    VirtualProtect(site, sizeof(expected), protection, &ignored);
    FlushInstructionCache(GetCurrentProcess(), site, sizeof(expected));
    Log("PRACTICE CUTSCENES READY: automatic completion enabled for this session.");
    return true;
}
