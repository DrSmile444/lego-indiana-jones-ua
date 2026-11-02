// Extract one complete UTF-8 character for the editor's fixed name cells.
// Never pass an isolated continuation/leading byte to the native renderer.
#include <stddef.h>
static bool EditorNameGlyph(const unsigned char *name, size_t capacity,
                            unsigned index, char output[5]) {
    bool non_ascii = false;
    for (size_t i = 0; i < capacity && name[i]; ++i)
        if (name[i] >= 0x80) non_ascii = true;
    if (!non_ascii) return false; // Preserve native ASCII editing/display.
    size_t position = 0;
    for (unsigned cell = 0; ; ++cell) {
        if (position >= capacity || !name[position]) {
            output[0] = ' '; output[1] = 0; return true;
        }
        unsigned char lead = name[position];
        size_t count = lead < 0x80 ? 1 :
            (lead >= 0xC2 && lead <= 0xDF ? 2 :
             (lead >= 0xE0 && lead <= 0xEF ? 3 :
              (lead >= 0xF0 && lead <= 0xF4 ? 4 : 0)));
        bool valid = count && count <= capacity - position;
        for (size_t j = 1; valid && j < count; ++j)
            valid = (name[position + j] & 0xC0) == 0x80;
        if (valid && count >= 3) {
            unsigned char second = name[position + 1];
            valid = !(lead == 0xE0 && second < 0xA0) &&
                    !(lead == 0xED && second >= 0xA0) &&
                    !(lead == 0xF0 && second < 0x90) &&
                    !(lead == 0xF4 && second >= 0x90);
        }
        if (cell == index) {
            if (!valid) { output[0] = '?'; output[1] = 0; return true; }
            for (size_t j = 0; j < count; ++j) output[j] = (char)name[position + j];
            output[count] = 0;
            return true;
        }
        position += valid ? count : 1;
    }
}
