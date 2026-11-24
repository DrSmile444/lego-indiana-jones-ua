// High-resolution fonts. The package carries UKRAINIAN/FONT_HD.DDS (Font 1) and
// UKRAINIAN/FONT2_HD.DDS (Font 2): each font atlas drawn k times larger, DXT5 with a full
// mip chain. The FNT files keep their original atlas size and metrics; their DDS header holds
// "UAHD", k and the atlas slot (0 = Font 1, 1 = Font 2) in dwReserved1[0..2]. The game loads
// font atlases with D3DXCreateTextureFromFileInMemory(Ex). When the source DDS has that mark
// and k times its size equals the slot's atlas, the plugin hands D3DX the large atlas instead
// and reports the original size in D3DXIMAGE_INFO and in GetLevelDesc of that texture
// (the game reads the atlas size from the texture to compute UVs), so metrics and UVs
// stay as before.
// If anything here fails, D3DX gets the game's own data and the 1x font shows.
#pragma once

#include <d3d9.h>

struct FontImageInfo {  // D3DXIMAGE_INFO
    UINT Width, Height, Depth, MipLevels;
    D3DFORMAT Format;
    D3DRESOURCETYPE ResourceType;
    int ImageFileFormat;
};
typedef HRESULT(WINAPI *FontCreateEx_t)(IDirect3DDevice9 *, const void *, UINT, UINT, UINT, UINT, DWORD,
                                        D3DFORMAT, D3DPOOL, DWORD, DWORD, D3DCOLOR, FontImageInfo *,
                                        PALETTEENTRY *, IDirect3DTexture9 **);
typedef HRESULT(WINAPI *FontCreate_t)(IDirect3DDevice9 *, const void *, UINT, IDirect3DTexture9 **);

static const char FONT_HD_DLL[] = "d3dx9_35.dll";
static const UINT D3DX_DEFAULT_VALUE = (UINT)-1;  // D3DX_DEFAULT
struct FontHdAtlas { const char *path; const BYTE *dds; UINT size, width, height; };
static FontHdAtlas font_hd[] = {{"UKRAINIAN/FONT_HD.DDS"}, {"UKRAINIAN/FONT2_HD.DDS"}};
static const UINT FONT_HD_SLOTS = sizeof(font_hd) / sizeof(font_hd[0]);
static FontCreateEx_t font_real_create_ex;
static FontCreate_t font_real_create;
static LONG font_hd_hits;
typedef HRESULT(STDMETHODCALLTYPE *FontLevelDesc_t)(IDirect3DTexture9 *, UINT, D3DSURFACE_DESC *);
static FontLevelDesc_t font_real_level_desc;
// {6B2E7C1A-5D44-4F0B-9C3E-2A71F0D5E8B4}: marks textures created by this file; data = k.
static const GUID FONT_HD_TAG = {0x6b2e7c1a, 0x5d44, 0x4f0b, {0x9c, 0x3e, 0x2a, 0x71, 0xf0, 0xd5, 0xe8, 0xb4}};

static HRESULT STDMETHODCALLTYPE FontLevelDesc(IDirect3DTexture9 *texture, UINT level, D3DSURFACE_DESC *desc) {
    HRESULT hr = font_real_level_desc(texture, level, desc);
    DWORD k = 0, size = sizeof(k);
    if (SUCCEEDED(hr) && desc && SUCCEEDED(texture->GetPrivateData(FONT_HD_TAG, &k, &size)) && k) {
        desc->Width = desc->Width / k ? desc->Width / k : 1;
        desc->Height = desc->Height / k ? desc->Height / k : 1;
    }
    return hr;
}

// Patches one vtable slot. A second vtable is patched only when its slot holds the same
// function, so the saved original is always the right one to call.
static bool FontPatchVtable(void **vt, int index, void *fn, void **orig) {
    if (vt[index] == fn) return true;
    if (*orig && vt[index] != *orig) return false;
    DWORD old;
    if (!VirtualProtect(&vt[index], sizeof(void *), PAGE_EXECUTE_READWRITE, &old)) return false;
    if (!*orig) *orig = vt[index];
    vt[index] = fn;
    VirtualProtect(&vt[index], sizeof(void *), old, &old);
    return true;
}

// Scale k when `data` is a marked 1x font atlas that a loaded atlas enlarges, else 0.
static UINT FontHdScale(const void *data, UINT size, const FontHdAtlas **atlas) {
    const BYTE *dds = (const BYTE *)data;
    if (!dds || size < 128 || memcmp(dds, "DDS ", 4) || memcmp(dds + 84, "DXT5", 4) || memcmp(dds + 32, "UAHD", 4))
        return 0;
    UINT height = *(const DWORD *)(dds + 12), width = *(const DWORD *)(dds + 16);
    UINT k = *(const DWORD *)(dds + 36), slot = *(const DWORD *)(dds + 40);
    if (slot >= FONT_HD_SLOTS || !font_hd[slot].dds) return 0;
    *atlas = &font_hd[slot];
    return k >= 2 && k <= 4 && width * k == font_hd[slot].width && height * k == font_hd[slot].height ? k : 0;
}

static HRESULT WINAPI FontCreateEx(IDirect3DDevice9 *device, const void *data, UINT size, UINT width, UINT height,
                                   UINT levels, DWORD usage, D3DFORMAT format, D3DPOOL pool, DWORD filter,
                                   DWORD mip_filter, D3DCOLOR key, FontImageInfo *info, PALETTEENTRY *palette,
                                   IDirect3DTexture9 **out) {
    const FontHdAtlas *atlas = NULL;
    UINT k = FontHdScale(data, size, &atlas);
    if (k && (format == D3DFMT_UNKNOWN || format == D3DFMT_DXT5)) {
        const BYTE *dds = (const BYTE *)data;
        UINT small_w = *(const DWORD *)(dds + 16), small_h = *(const DWORD *)(dds + 12);
        UINT small_levels = *(const DWORD *)(dds + 28);
        // Exact size (D3DX_DEFAULT would round 3072 up to 4096); every level comes from the file.
        HRESULT hr = font_real_create_ex(device, atlas->dds, atlas->size, atlas->width, atlas->height, 0, usage,
                                         format, pool, filter,
                                         mip_filter, key, info, palette, out);
        DWORD tag = k;
        if (SUCCEEDED(hr) && (FAILED((*out)->SetPrivateData(FONT_HD_TAG, &tag, sizeof(tag), 0)) ||
                              !FontPatchVtable(*(void ***)*out, 17, (void *)&FontLevelDesc,
                                               (void **)&font_real_level_desc))) {
            (*out)->Release();
            *out = NULL;
            hr = E_FAIL;
        }
        if (SUCCEEDED(hr)) {
            if (info) { info->Width = small_w; info->Height = small_h; info->MipLevels = small_levels ? small_levels : 1; }
            if (InterlockedIncrement(&font_hd_hits) <= 4) {
                char message[200];
                sprintf_s(message, "FONT HD: %s %ux%u x%u texture for the %ux%u font atlas (format %d, pool %d).",
                          atlas->path, atlas->width, atlas->height, k, small_w, small_h, (int)format, (int)pool);
                Log(message);
            }
            return hr;
        }
        if (InterlockedIncrement(&font_hd_hits) <= 4)
            Log("FONT HD: D3DX rejected the high-resolution atlas; the original font stays.");
    }
    return font_real_create_ex(device, data, size, width, height, levels, usage, format, pool, filter, mip_filter,
                               key, info, palette, out);
}

static HRESULT WINAPI FontCreate(IDirect3DDevice9 *device, const void *data, UINT size, IDirect3DTexture9 **out) {
    const FontHdAtlas *atlas = NULL;
    if (FontHdScale(data, size, &atlas) && font_real_create_ex)
        return FontCreateEx(device, data, size, D3DX_DEFAULT_VALUE, D3DX_DEFAULT_VALUE, D3DX_DEFAULT_VALUE, 0,
                            D3DFMT_UNKNOWN, D3DPOOL_MANAGED, (DWORD)D3DX_DEFAULT_VALUE, (DWORD)D3DX_DEFAULT_VALUE, 0, NULL, NULL,
                            out);
    return font_real_create(device, data, size, out);
}

// Replaces one import of the game EXE; returns the previous function or NULL.
static void *FontPatchImport(const char *dll, const char *name, void *replacement) {
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY &dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return NULL;
    for (IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress); imp->Name; ++imp) {
        if (_stricmp((char *)(base + imp->Name), dll) != 0) continue;
        IMAGE_THUNK_DATA *thunk = (IMAGE_THUNK_DATA *)(base + imp->FirstThunk);
        IMAGE_THUNK_DATA *orig = (IMAGE_THUNK_DATA *)(base + (imp->OriginalFirstThunk ? imp->OriginalFirstThunk
                                                                                     : imp->FirstThunk));
        for (; orig->u1.AddressOfData; ++orig, ++thunk) {
            if (IMAGE_SNAP_BY_ORDINAL(orig->u1.Ordinal)) continue;
            if (strcmp((char *)((IMAGE_IMPORT_BY_NAME *)(base + orig->u1.AddressOfData))->Name, name) != 0) continue;
            DWORD old;
            void *previous = (void *)thunk->u1.Function;
            if (!VirtualProtect(&thunk->u1.Function, sizeof(void *), PAGE_READWRITE, &old)) return NULL;
            thunk->u1.Function = (ULONG_PTR)replacement;
            VirtualProtect(&thunk->u1.Function, sizeof(void *), old, &old);
            return previous;
        }
    }
    return NULL;
}

// Checks one atlas from the package; leaves the slot empty when it is missing or invalid.
static void LoadFontHdAtlas(FontHdAtlas &atlas) {
    UapEntry *entry = FindUap(atlas.path);
    if (!entry) return;
    const BYTE *dds = uap_bytes + entry->offset;
    char message[200];
    if (entry->size < 128 || memcmp(dds, "DDS ", 4) || memcmp(dds + 84, "DXT5", 4)) {
        sprintf_s(message, "FONT HD SKIP: %s is not a DXT5 DDS.", atlas.path);
        Log(message);
        return;
    }
    UINT height = *(const DWORD *)(dds + 12), width = *(const DWORD *)(dds + 16), levels = *(const DWORD *)(dds + 28);
    UINT bytes = 128, full = 1;
    for (UINT w = width, h = height; w > 1 || h > 1; ++full) { w = w > 1 ? w / 2 : 1; h = h > 1 ? h / 2 : 1; }
    for (UINT i = 0; i < levels; ++i) {
        UINT w = width >> i, h = height >> i;
        bytes += ((w ? w : 1) + 3) / 4 * (((h ? h : 1) + 3) / 4) * 16;
    }
    if (!width || !height || levels != full || bytes != entry->size) {
        sprintf_s(message, "FONT HD SKIP: %s has an unexpected size or mip chain.", atlas.path);
        Log(message);
        return;
    }
    atlas.dds = dds; atlas.size = entry->size; atlas.width = width; atlas.height = height;
    sprintf_s(message, "FONT HD: %s %ux%u ready.", atlas.path, width, height);
    Log(message);
}

static void InitializeFontHd() {
    bool any = false;
    for (UINT i = 0; i < FONT_HD_SLOTS; ++i) {
        LoadFontHdAtlas(font_hd[i]);
        any = any || font_hd[i].dds;
    }
    if (!any) return;
    font_real_create_ex = (FontCreateEx_t)FontPatchImport(FONT_HD_DLL, "D3DXCreateTextureFromFileInMemoryEx",
                                                         (void *)&FontCreateEx);
    font_real_create = (FontCreate_t)FontPatchImport(FONT_HD_DLL, "D3DXCreateTextureFromFileInMemory",
                                                    (void *)&FontCreate);
    char message[160];
    sprintf_s(message, "FONT HD: D3DX hooks: Ex %s, plain %s.", font_real_create_ex ? "installed" : "NOT installed",
              font_real_create ? "installed" : "NOT installed");
    Log(message);
}
