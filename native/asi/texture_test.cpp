// Run the production buffer patcher against original GSCs and reviewed output.
#include <windows.h>
#include <bcrypt.h>
#include <stdio.h>
#include <vector>
#include <string.h>
#pragma pack(push, 1)
struct UapEntry { char path[256]; DWORD offset, size; BYTE sha256[32]; };
#pragma pack(pop)
static BYTE *uap_bytes;
static DWORD uap_count;
static UapEntry *uap_entries;
static unsigned patches;
static void Log(const char *message) {
    if (!strncmp(message, "UAP DDS BUFFER PATCH:", 21)) ++patches;
    else fprintf(stderr, "%s\n", message);
}
#include "texture_buffer.h"
static std::vector<BYTE> Load(const char *path) {
    FILE *file = NULL;
    if (fopen_s(&file, path, "rb") || !file) return {};
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    rewind(file);
    if (size <= 0) { fclose(file); return {}; }
    std::vector<BYTE> bytes((size_t)size);
    if (fread(bytes.data(), 1, bytes.size(), file) != bytes.size()) bytes.clear();
    fclose(file);
    return bytes;
}
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    auto pack = Load(argv[1]), original = Load(argv[2]), expected = Load(argv[3]);
    if (pack.size() < 12 || original.empty() || expected.empty()) return 3;
    uap_bytes = pack.data();
    uap_count = *(DWORD *)(uap_bytes + 8);
    if (uap_count > 64 || 12 + uap_count * sizeof(UapEntry) > pack.size()) return 4;
    uap_entries = (UapEntry *)(uap_bytes + 12);
    InitializeUapTextureIndex();
    if (uap_texture_count != 9) return 5;
    // Exercise mod conflicts on actual original pixels, before any replacement.
    for (size_t i = 0; i + 128 <= original.size(); ++i) {
        if (memcmp(original.data() + i, "DDS ", 4)) continue;
        UapEntry *entry = SelectUapDds(original.data() + i, (UINT)(original.size() - i));
        if (!entry) continue;
        std::vector<BYTE> modified(original.data() + i, original.data() + i + entry->size);
        modified[128] ^= 1;
        auto before = modified;
        PatchUapDds(modified.data(), (DWORD)modified.size());
        if (modified != before) return 8;
        // The game may rewrite DDS flags while keeping the image payload intact.
        modified[128] ^= 1;
        modified[8] ^= 1;
        PatchUapDds(modified.data(), (DWORD)modified.size());
        if (memcmp(modified.data(), uap_bytes + entry->offset, entry->size)) return 9;
    }
    patches = 0;
    PatchUapDds(original.data(), (DWORD)original.size());
    if (!patches || original != expected) return 6;
    unsigned first_pass = patches;
    PatchUapDds(original.data(), (DWORD)original.size());
    if (patches != first_pass || original != expected) return 7;
    printf("PASS: %u replacements; exact full-resource match; idempotent; changed pixels preserved\n", first_pass);
    return 0;
}
