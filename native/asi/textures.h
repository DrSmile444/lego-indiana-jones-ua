#include "texture_buffer.h"
typedef int (__cdecl *ReadNativeResource)(int, void *, int);
static ReadNativeResource original_read_resource;
static int __cdecl ReadUapResource(int handle, void *destination, int requested) {
    int result = original_read_resource(handle, destination, requested);
    if (result > 0) PatchUapDds((BYTE *)destination, (DWORD)result);
    return result;
}
static void InitializeUapTextures(BYTE *base) {
    InitializeUapTextureIndex();
    if (!uap_texture_count) return;
    BYTE *read_site = base + 0x2B55A0;
    const BYTE expected_read[] = {0x51, 0x8B, 0x44, 0x24, 0x08};
    if (memcmp(read_site, expected_read, 5)) { Log("UAP TEXTURE SKIP: native read differs."); return; }
    original_read_resource = (ReadNativeResource)MakeTrampoline(read_site, 5);
    if (!original_read_resource || !SetJump(read_site, (void *)&ReadUapResource, 5)) {
        Log("UAP TEXTURE SKIP: native read hook failed."); return;
    }
    char message[120];
    sprintf_s(message, "UAP TEXTURES READY: %lu DDS replacements; original GSC containers remain in DAT.", uap_texture_count);
    Log(message);
}
