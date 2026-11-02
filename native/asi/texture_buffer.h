// Replace only reviewed DDS payloads; preserve every other resource byte.
struct TextureReplacement { UapEntry *entry; BYTE original_sha256[32]; };
static TextureReplacement uap_textures[32];
static DWORD uap_texture_count;

static bool HashDds(const BYTE *bytes, DWORD size, BYTE digest[32]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    bool ok = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0) >= 0 &&
        BCryptCreateHash(algorithm, &hash, NULL, 0, NULL, 0, 0) >= 0 &&
        BCryptHashData(hash, (PUCHAR)bytes, size, 0) >= 0 &&
        BCryptFinishHash(hash, digest, 32, 0) >= 0;
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    return ok;
}
static bool ReadableDds(const BYTE *data, SIZE_T size) {
    const BYTE *end = data + size;
    if (end < data) return false;
    while (data < end) {
        MEMORY_BASIC_INFORMATION info;
        if (!VirtualQuery(data, &info, sizeof(info)) || info.State != MEM_COMMIT ||
            (info.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
        const BYTE *region_end = (const BYTE *)info.BaseAddress + info.RegionSize;
        if (region_end <= data) return false;
        data = region_end;
    }
    return true;
}
static UapEntry *SelectUapDds(const void *source, UINT source_size) {
    const BYTE *bytes = (const BYTE *)source;
    if (bytes && source_size >= 128 && ReadableDds(bytes, 128) && !memcmp(bytes, "DDS ", 4)) {
        DWORD hashed_size = 0;
        BYTE digest[32];
        bool hashed = false;
        for (DWORD i = 0; i < uap_texture_count; ++i) {
            TextureReplacement &replacement = uap_textures[i];
            UapEntry &entry = *replacement.entry;
            BYTE *translated = uap_bytes + entry.offset;
            if (entry.size > source_size || memcmp(bytes + 12, translated + 12, 8) ||
                memcmp(bytes + 84, translated + 84, 4) || memcmp(bytes + 28, translated + 28, 4)) continue;
            if (hashed_size != entry.size) {
                hashed_size = entry.size;
                hashed = ReadableDds(bytes, entry.size) && HashDds(bytes + 128, entry.size - 128, digest);

            }
            if (!hashed || memcmp(digest, replacement.original_sha256, 32)) continue;
            return &entry;
        }
    }
    return NULL;
}
static void PatchUapDds(BYTE *bytes, DWORD size) {
    if (!uap_texture_count || !bytes || size < 128) return;
    DWORD position = 0;
    while (position <= size - 128) {
        BYTE *found = (BYTE *)memchr(bytes + position, 'D', size - 128 - position + 1);
        if (!found) break;
        position = (DWORD)(found - bytes);
        if (!memcmp(found, "DDS ", 4)) {
            UapEntry *entry = SelectUapDds(found, size - position);
            if (entry) {
                memcpy(found, uap_bytes + entry->offset, entry->size);
                char message[180];
                sprintf_s(message, "UAP DDS BUFFER PATCH: %.64s bytes=%lu offset=%lu", entry->path + 19, entry->size, position);
                Log(message);
                position += entry->size;
                continue;
            }
        }
        ++position;
    }
}
static int HexDigit(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'A' && value <= 'F') return value - 'A' + 10;
    return -1;
}
static void InitializeUapTextureIndex() {
    const char *prefix = "UKRAINIAN/TEXTURES/";
    const size_t prefix_size = strlen(prefix);
    for (DWORD i = 0; i < uap_count; ++i) {
        UapEntry &entry = uap_entries[i];
        if (strncmp(entry.path, prefix, prefix_size)) continue;
        if (strlen(entry.path) != prefix_size + 68 || strcmp(entry.path + prefix_size + 64, ".DDS") ||
            entry.size < 128 || memcmp(uap_bytes + entry.offset, "DDS ", 4) || uap_texture_count >= 32) {
            Log("UAP TEXTURE SKIP: invalid texture metadata."); uap_texture_count = 0; return;
        }
        TextureReplacement &replacement = uap_textures[uap_texture_count];
        replacement.entry = &entry;
        for (int j = 0; j < 32; ++j) {
            int high = HexDigit(entry.path[prefix_size + j * 2]);
            int low = HexDigit(entry.path[prefix_size + j * 2 + 1]);
            if (high < 0 || low < 0) { Log("UAP TEXTURE SKIP: invalid source hash."); uap_texture_count = 0; return; }
            replacement.original_sha256[j] = (BYTE)((high << 4) | low);
        }
        ++uap_texture_count;
    }
    if (!uap_texture_count) return;
}
