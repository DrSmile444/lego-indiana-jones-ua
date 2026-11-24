// Development-only test mode, enabled by scripts/UKRAINIAN.test.ini next to the plugin.
// Never shipped to players: the package builder does not include the ini, and
// without it nothing here is installed.
//   [Test] Borderless=1      captionless window over the monitor instead of exclusive fullscreen
//   [Test] ScreenshotKey=0x7B save the next frame as scripts/screens/<n>.bmp on that key
//   [Test] KeepRunning=1     keep updating and rendering while the window is in the background
//   [Test] VirtualKeys=1     keyboard input from scripts/screens/keys.txt (no focus needed)
//   [Test] Locale=0x0422      report this LCID from GetUserDefaultLCID/GetUserDefaultLangID,
//                             to test how the game picks its language under other system locales
// Automation can also request a frame by creating scripts/screens/request.txt with
// the target file name; the plugin writes scripts/screens/<name>.bmp and deletes the request.
// Based on the display code of the LEGO Indiana Jones multiplayer research (d3d.h).
#include <stdlib.h>
#include <d3d9.h>
#define DIRECTINPUT_VERSION 0x0800
#include <dinput.h>
#pragma comment(lib, "user32.lib")

typedef IDirect3D9 *(WINAPI *Direct3DCreate9_t)(UINT);
typedef HRESULT(STDMETHODCALLTYPE *CreateDevice_t)(IDirect3D9 *, UINT, D3DDEVTYPE, HWND, DWORD,
                                                   D3DPRESENT_PARAMETERS *, IDirect3DDevice9 **);
typedef HRESULT(STDMETHODCALLTYPE *Reset_t)(IDirect3DDevice9 *, D3DPRESENT_PARAMETERS *);
typedef HRESULT(STDMETHODCALLTYPE *Present_t)(IDirect3DDevice9 *, const RECT *, const RECT *, HWND, const RGNDATA *);

static Direct3DCreate9_t test_real_create9;
static CreateDevice_t test_real_create_device;
static Reset_t test_real_reset;
static Present_t test_real_present;
static bool test_borderless;
static int test_screenshot_key;
static HWND test_hwnd;
static wchar_t test_screens_dir[MAX_PATH];
static unsigned test_frame;
static int test_shot_number;
static LCID test_locale;

static LCID WINAPI TestUserLcid() { return test_locale; }
static LANGID WINAPI TestUserLangId() { return LANGIDFROMLCID(test_locale); }

static void TestPath(wchar_t *out, const wchar_t *name) {
    wcscpy_s(out, MAX_PATH, test_screens_dir);
    wcscat_s(out, MAX_PATH, name);
}

static void TestFixWindow(HWND hwnd) {
    if (!hwnd) return;
    test_hwnd = hwnd;
    LONG style = GetWindowLongA(hwnd, GWL_STYLE);
    style &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME);
    style |= WS_POPUP | WS_VISIBLE;
    SetWindowLongA(hwnd, GWL_STYLE, style);
    LONG ex = GetWindowLongA(hwnd, GWL_EXSTYLE);
    SetWindowLongA(hwnd, GWL_EXSTYLE, ex & ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE |
                                             WS_EX_STATICEDGE | WS_EX_TOPMOST));
    MONITORINFO mi = {sizeof(mi)};
    GetMonitorInfoA(MonitorFromWindow(hwnd, MONITOR_DEFAULTTOPRIMARY), &mi);
    const RECT &m = mi.rcMonitor;
    // Behind every other window and never activated: the game renders and is captured without focus.
    SetWindowPos(hwnd, HWND_BOTTOM, m.left, m.top, m.right - m.left, m.bottom - m.top,
                 SWP_SHOWWINDOW | SWP_FRAMECHANGED | SWP_NOACTIVATE);
}

static void TestFixParams(D3DPRESENT_PARAMETERS *pp) {
    pp->Windowed = TRUE;
    pp->FullScreen_RefreshRateInHz = 0;
    if (pp->PresentationInterval == 0) pp->PresentationInterval = D3DPRESENT_INTERVAL_ONE;
}

static void TestWriteBmp(IDirect3DDevice9 *dev, const wchar_t *path) {
    IDirect3DSurface9 *bb = NULL, *sys = NULL;
    if (FAILED(dev->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO, &bb))) return;
    D3DSURFACE_DESC d;
    bb->GetDesc(&d);
    if ((d.Format == D3DFMT_X8R8G8B8 || d.Format == D3DFMT_A8R8G8B8) &&
        SUCCEEDED(dev->CreateOffscreenPlainSurface(d.Width, d.Height, d.Format, D3DPOOL_SYSTEMMEM, &sys, NULL)) &&
        SUCCEEDED(dev->GetRenderTargetData(bb, sys))) {
        D3DLOCKED_RECT lr;
        if (SUCCEEDED(sys->LockRect(&lr, NULL, D3DLOCK_READONLY))) {
            HANDLE f = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL);
            if (f != INVALID_HANDLE_VALUE) {
                BITMAPFILEHEADER fh = {};
                BITMAPINFOHEADER ih = {};
                ih.biSize = sizeof(ih);
                ih.biWidth = (LONG)d.Width;
                ih.biHeight = -(LONG)d.Height;
                ih.biPlanes = 1;
                ih.biBitCount = 32;
                fh.bfType = 0x4d42;
                fh.bfOffBits = sizeof(fh) + sizeof(ih);
                fh.bfSize = fh.bfOffBits + d.Width * d.Height * 4;
                DWORD w;
                WriteFile(f, &fh, sizeof(fh), &w, NULL);
                WriteFile(f, &ih, sizeof(ih), &w, NULL);
                for (UINT y = 0; y < d.Height; ++y) WriteFile(f, (BYTE *)lr.pBits + y * lr.Pitch, d.Width * 4, &w, NULL);
                CloseHandle(f);
            }
            sys->UnlockRect();
        }
    }
    if (sys) sys->Release();
    bb->Release();
}

static void TestScreenshots(IDirect3DDevice9 *dev) {
    wchar_t path[MAX_PATH];
    static bool key_down;
    if (test_screenshot_key) {
        bool down = (GetAsyncKeyState(test_screenshot_key) & 0x8000) != 0;
        if (down && !key_down) {
            wchar_t name[32];
            swprintf_s(name, L"shot-%03d.bmp", ++test_shot_number);
            TestPath(path, name);
            TestWriteBmp(dev, path);
        }
        key_down = down;
    }
    if (++test_frame % 15) return;
    wchar_t request[MAX_PATH];
    TestPath(request, L"request.txt");
    HANDLE f = CreateFileW(request, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return;
    char name[64] = {};
    DWORD got = 0;
    ReadFile(f, name, sizeof(name) - 1, &got, NULL);
    CloseHandle(f);
    DeleteFileW(request);
    wchar_t wide[64] = {};
    int n = 0;
    for (DWORD i = 0; i < got && n < 48; ++i) {
        char c = name[i];
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_') wide[n++] = c;
    }
    if (!n) return;
    wcscat_s(wide, L".bmp");
    TestPath(path, wide);
    TestWriteBmp(dev, path);
}

static HRESULT STDMETHODCALLTYPE TestPresent(IDirect3DDevice9 *dev, const RECT *a, const RECT *b, HWND w,
                                            const RGNDATA *r) {
    TestScreenshots(dev);
    return test_real_present(dev, a, b, w, r);
}

static HRESULT STDMETHODCALLTYPE TestReset(IDirect3DDevice9 *dev, D3DPRESENT_PARAMETERS *pp) {
    if (test_borderless) TestFixParams(pp);
    HRESULT hr = test_real_reset(dev, pp);
    if (test_borderless) TestFixWindow(test_hwnd);
    return hr;
}

static void TestPatchVtable(void **vt, int index, void *fn, void **orig) {
    if (vt[index] == fn) return;
    if (!*orig) *orig = vt[index];
    DWORD old;
    VirtualProtect(&vt[index], sizeof(void *), PAGE_READWRITE, &old);
    vt[index] = fn;
    VirtualProtect(&vt[index], sizeof(void *), old, &old);
}

static HRESULT STDMETHODCALLTYPE TestCreateDevice(IDirect3D9 *d3d, UINT adapter, D3DDEVTYPE type, HWND focus,
                                                 DWORD flags, D3DPRESENT_PARAMETERS *pp, IDirect3DDevice9 **out) {
    if (test_borderless) {
        TestFixParams(pp);
        TestFixWindow(pp->hDeviceWindow ? pp->hDeviceWindow : focus);
    }
    HRESULT hr = test_real_create_device(d3d, adapter, type, focus, flags, pp, out);
    char message[160];
    sprintf_s(message, "TEST D3D: CreateDevice %ux%u windowed=%d -> 0x%08lx", pp->BackBufferWidth,
              pp->BackBufferHeight, pp->Windowed, (unsigned long)hr);
    Log(message);
    if (SUCCEEDED(hr) && out && *out) {
        TestPatchVtable(*(void ***)*out, 16, (void *)&TestReset, (void **)&test_real_reset);
        TestPatchVtable(*(void ***)*out, 17, (void *)&TestPresent, (void **)&test_real_present);
    }
    return hr;
}

static IDirect3D9 *WINAPI TestCreate9(UINT sdk) {
    IDirect3D9 *d3d = test_real_create9(sdk);
    if (d3d) TestPatchVtable(*(void ***)d3d, 16, (void *)&TestCreateDevice, (void **)&test_real_create_device);
    return d3d;
}

// The window procedure 0x5205C0 jumps to 0x520639 on WM_KILLFOCUS and on an inactive
// WM_ACTIVATE / WM_ACTIVATEAPP; that path stores 0 into the active flag [0x921B00]. While the
// flag is 0 the frame and main loops sleep and skip update and rendering, so the game freezes
// without focus. In test mode that path stores 1: `mov dword [0x921B00], 0` -> `..., 1`.
// Keyboard input without focus comes from the virtual keyboard below (VirtualKeys).
#define RVA_DEACTIVATE_PATH 0x120639
#define RVA_ACTIVE_FLAG 0x521B00
static const BYTE expect_deactivate[] = {0x5F, 0x5E, 0x5D, 0xC7, 0x05, 0x00, 0x1B, 0x92, 0x00, 0x00,
                                         0x00, 0x00, 0x00, 0x33, 0xC0, 0x5B, 0xC2, 0x10, 0x00};

static bool TestKeepRunning() {
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
    BYTE *site = base + RVA_DEACTIVATE_PATH;
    if (memcmp(site, expect_deactivate, sizeof(expect_deactivate)) != 0) return false;
    DWORD old;
    if (!VirtualProtect(site + 9, 1, PAGE_EXECUTE_READWRITE, &old)) return false;
    site[9] = 0x01;
    VirtualProtect(site + 9, 1, old, &old);
    FlushInstructionCache(GetCurrentProcess(), site + 9, 1);
    *(volatile DWORD *)(base + RVA_ACTIVE_FLAG) = 1;
    return true;
}

// Virtual keyboard: automation holds keys by writing DirectInput scan codes (hex,
// space-separated) to scripts/screens/keys.txt, so the game needs no focus and
// nothing is typed into the user's foreground window. The keyboard device runs in
// background mode; its real state is cleared while the game is not in the foreground.
#define TEST_DI_VTABLE_CREATE_DEVICE 3
#define TEST_DID_VTABLE_GET_STATE 9
#define TEST_DID_VTABLE_GET_DATA 10
#define TEST_DID_VTABLE_COOPERATIVE 13
static const GUID test_sys_keyboard = {0x6F1D2B61, 0xD5A0, 0x11CF, {0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00}};
typedef HRESULT(WINAPI *DirectInput8Create_t)(HINSTANCE, DWORD, REFIID, void **, IUnknown *);
typedef HRESULT(STDMETHODCALLTYPE *DiCreateDevice_t)(void *, REFGUID, void **, IUnknown *);
typedef HRESULT(STDMETHODCALLTYPE *DidGetState_t)(void *, DWORD, void *);
typedef HRESULT(STDMETHODCALLTYPE *DidGetData_t)(void *, DWORD, void *, DWORD *, DWORD);
typedef HRESULT(STDMETHODCALLTYPE *DidCooperative_t)(void *, HWND, DWORD);
static DirectInput8Create_t test_real_di8_create;
static DiCreateDevice_t test_real_di_create_device;
static DidGetState_t test_real_get_state;
static DidGetData_t test_real_get_data;
static DidCooperative_t test_real_cooperative;
static void *test_keyboard;
static BYTE test_virtual_keys[256];
static DWORD test_keys_checked;
static LONG test_keyboard_reads, test_keyboard_buffered;

static void TestReadVirtualKeys() {
    DWORD now = GetTickCount();
    if (now - test_keys_checked < 20) return;
    test_keys_checked = now;
    memset(test_virtual_keys, 0, sizeof(test_virtual_keys));
    wchar_t path[MAX_PATH];
    TestPath(path, L"keys.txt");
    HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL,
                           OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return;
    char text[256] = {};
    DWORD got = 0;
    ReadFile(f, text, sizeof(text) - 1, &got, NULL);
    CloseHandle(f);
    for (char *p = text; *p;) {
        char *end;
        unsigned long code = strtoul(p, &end, 16);
        if (end == p) { ++p; continue; }
        if (code < 256) test_virtual_keys[code] = 0x80;
        p = end;
    }
}

static bool TestGameInForeground() {
    DWORD pid = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &pid);
    return pid == GetCurrentProcessId();
}

static HRESULT STDMETHODCALLTYPE TestGetState(void *device, DWORD size, void *data) {
    HRESULT hr = test_real_get_state(device, size, data);
    if (device != test_keyboard || size != 256 || !data) return hr;
    if (InterlockedIncrement(&test_keyboard_reads) == 1) Log("TEST KEYS: the game reads the keyboard state.");
    if (FAILED(hr) || !TestGameInForeground()) memset(data, 0, size);
    TestReadVirtualKeys();
    for (int i = 0; i < 256; ++i) ((BYTE *)data)[i] |= test_virtual_keys[i];
    return DI_OK;
}

static HRESULT STDMETHODCALLTYPE TestGetData(void *device, DWORD size, void *data, DWORD *count, DWORD flags) {
    HRESULT hr = test_real_get_data(device, size, data, count, flags);
    if (device == test_keyboard && InterlockedIncrement(&test_keyboard_buffered) == 1)
        Log("TEST KEYS: the game also reads buffered keyboard data (not virtualized).");
    if (device == test_keyboard && count && !TestGameInForeground()) *count = 0;
    return hr;
}

static HRESULT STDMETHODCALLTYPE TestCooperative(void *device, HWND hwnd, DWORD flags) {
    if (device == test_keyboard) flags = DISCL_BACKGROUND | DISCL_NONEXCLUSIVE;
    return test_real_cooperative(device, hwnd, flags);
}

static HRESULT STDMETHODCALLTYPE TestDiCreateDevice(void *di, REFGUID guid, void **out, IUnknown *outer) {
    HRESULT hr = test_real_di_create_device(di, guid, out, outer);
    if (SUCCEEDED(hr) && out && *out && IsEqualGUID(guid, test_sys_keyboard)) {
        test_keyboard = *out;
        void **vt = *(void ***)*out;
        TestPatchVtable(vt, TEST_DID_VTABLE_GET_STATE, (void *)&TestGetState, (void **)&test_real_get_state);
        TestPatchVtable(vt, TEST_DID_VTABLE_GET_DATA, (void *)&TestGetData, (void **)&test_real_get_data);
        TestPatchVtable(vt, TEST_DID_VTABLE_COOPERATIVE, (void *)&TestCooperative, (void **)&test_real_cooperative);
        Log("TEST KEYS: virtual keyboard attached (scripts/screens/keys.txt).");
    }
    return hr;
}

static HRESULT WINAPI TestDi8Create(HINSTANCE instance, DWORD version, REFIID iid, void **out, IUnknown *outer) {
    HRESULT hr = test_real_di8_create(instance, version, iid, out, outer);
    if (SUCCEEDED(hr) && out && *out)
        TestPatchVtable(*(void ***)*out, TEST_DI_VTABLE_CREATE_DEVICE, (void *)&TestDiCreateDevice,
                        (void **)&test_real_di_create_device);
    return hr;
}

static void *TestPatchImport(const char *dll, const char *name, void *replacement) {
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)base;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + dos->e_lfanew);
    IMAGE_DATA_DIRECTORY &dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return NULL;
    for (IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress); imp->Name; ++imp) {
        if (_stricmp((char *)(base + imp->Name), dll) != 0) continue;
        IMAGE_THUNK_DATA *thunk = (IMAGE_THUNK_DATA *)(base + imp->FirstThunk);
        IMAGE_THUNK_DATA *orig = (IMAGE_THUNK_DATA *)(base + (imp->OriginalFirstThunk ? imp->OriginalFirstThunk : imp->FirstThunk));
        for (; orig->u1.AddressOfData; ++orig, ++thunk) {
            if (IMAGE_SNAP_BY_ORDINAL(orig->u1.Ordinal)) continue;
            IMAGE_IMPORT_BY_NAME *ibn = (IMAGE_IMPORT_BY_NAME *)(base + orig->u1.AddressOfData);
            if (strcmp((char *)ibn->Name, name) != 0) continue;
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

static void InitializeTestMode() {
    wchar_t ini[MAX_PATH];
    if (!GetModuleFileNameW(self_module, ini, MAX_PATH)) return;
    wchar_t *name = wcsrchr(ini, L'\\');
    if (!name) return;
    name[1] = 0;
    wcscpy_s(test_screens_dir, ini);
    wcscat_s(test_screens_dir, L"screens\\");
    if (wcscpy_s(name + 1, MAX_PATH - (name + 1 - ini), L"UKRAINIAN.test.ini")) return;
    if (GetFileAttributesW(ini) == INVALID_FILE_ATTRIBUTES) return;  // player install: nothing to do
    test_borderless = GetPrivateProfileIntW(L"Test", L"Borderless", 0, ini) != 0;
    wchar_t key[16];
    GetPrivateProfileStringW(L"Test", L"ScreenshotKey", L"0", key, 16, ini);
    test_screenshot_key = (int)wcstol(key, NULL, 0);
    CreateDirectoryW(test_screens_dir, NULL);
    test_real_create9 = (Direct3DCreate9_t)TestPatchImport("d3d9.dll", "Direct3DCreate9", (void *)&TestCreate9);
    char message[160];
    sprintf_s(message, "TEST MODE: borderless=%d screenshot_key=0x%X d3d9 hook %s", test_borderless,
              test_screenshot_key, test_real_create9 ? "installed" : "NOT installed");
    Log(message);
    if (GetPrivateProfileIntW(L"Test", L"KeepRunning", 1, ini) != 0) {
        Log(TestKeepRunning() ? "TEST KEEP RUNNING: the game updates and renders without focus."
                              : "TEST KEEP RUNNING: unexpected window procedure bytes; not patched.");
    }
    if (GetPrivateProfileIntW(L"Test", L"VirtualKeys", 1, ini) != 0) {
        test_real_di8_create = (DirectInput8Create_t)TestPatchImport("dinput8.dll", "DirectInput8Create",
                                                                     (void *)&TestDi8Create);
        Log(test_real_di8_create ? "TEST KEYS: DirectInput8Create hook installed."
                                 : "TEST KEYS: DirectInput8Create import not found.");
    }
    wchar_t locale[16];
    GetPrivateProfileStringW(L"Test", L"Locale", L"0", locale, 16, ini);
    test_locale = (LCID)wcstoul(locale, NULL, 0);
    if (test_locale) {
        bool lcid = TestPatchImport("kernel32.dll", "GetUserDefaultLCID", (void *)&TestUserLcid) != NULL;
        bool langid = TestPatchImport("kernel32.dll", "GetUserDefaultLangID", (void *)&TestUserLangId) != NULL;
        sprintf_s(message, "TEST LOCALE: 0x%04lX; GetUserDefaultLCID hook %s, GetUserDefaultLangID hook %s",
                  (unsigned long)test_locale, lcid ? "installed" : "NOT installed",
                  langid ? "installed" : "NOT installed");
        Log(message);
    }
}
