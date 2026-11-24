// Development-only test mode, enabled by scripts/UKRAINIAN.test.ini next to the plugin.
// Never shipped to players: the package builder does not include the ini, and
// without it nothing here is installed.
//   [Test] Borderless=1      captionless window over the monitor instead of exclusive fullscreen
//   [Test] ScreenshotKey=0x7B save the next frame as scripts/screens/<n>.bmp on that key
//   [Test] KeepRunning=1     keep updating and rendering while the window is in the background
//   [Test] VirtualKeys=1     keyboard input from scripts/screens/keys.txt (no focus needed)
//   [Test] VirtualPad=1      an Xbox 360 pad (DirectInput + XInput user 0) whose buttons come from
//                             scripts/screens/pad.txt (hex XINPUT wButtons): controller prompts
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

// Virtual gamepad: XInput user 0 is a connected pad; its buttons (hex XINPUT_GAMEPAD wButtons)
// come from scripts/screens/pad.txt. The game imports XInput by ordinal.
struct TestPad { WORD buttons; BYTE lt, rt; SHORT lx, ly, rx, ry; };
struct TestPadState { DWORD packet; TestPad pad; };
struct TestPadCaps { BYTE type, subtype; WORD flags; TestPad pad; WORD left_motor, right_motor; };
typedef DWORD(WINAPI *XInputGetState_t)(DWORD, TestPadState *);
typedef DWORD(WINAPI *XInputGetCaps_t)(DWORD, DWORD, TestPadCaps *);
static XInputGetState_t test_real_xinput_state;
static XInputGetCaps_t test_real_xinput_caps;
static DWORD test_pad_packet;

static WORD TestReadPad() {
    wchar_t path[MAX_PATH];
    TestPath(path, L"pad.txt");
    HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL,
                           OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) return 0;
    char text[32] = {};
    DWORD got = 0;
    ReadFile(f, text, sizeof(text) - 1, &got, NULL);
    CloseHandle(f);
    return (WORD)strtoul(text, NULL, 16);
}

static DWORD WINAPI TestXInputState(DWORD user, TestPadState *state) {
    static LONG calls;
    if (InterlockedIncrement(&calls) == 1) Log("TEST PAD: the game reads XInput state.");
    if (user != 0 || !state) return test_real_xinput_state ? test_real_xinput_state(user, state) : 1167;
    memset(state, 0, sizeof(*state));
    state->pad.buttons = TestReadPad();
    state->packet = ++test_pad_packet;
    return ERROR_SUCCESS;
}

static DWORD WINAPI TestXInputCaps(DWORD user, DWORD flags, TestPadCaps *caps) {
    static LONG calls;
    if (InterlockedIncrement(&calls) == 1) Log("TEST PAD: the game reads XInput capabilities.");
    if (user != 0 || !caps) return test_real_xinput_caps ? test_real_xinput_caps(user, flags, caps) : 1167;
    memset(caps, 0, sizeof(*caps));
    caps->type = 1;     // XINPUT_DEVTYPE_GAMEPAD
    caps->subtype = 1;  // XINPUT_DEVSUBTYPE_GAMEPAD
    caps->pad.buttons = 0xF3FF;
    caps->pad.lt = caps->pad.rt = 0xFF;
    return ERROR_SUCCESS;
}

// The engine finds gamepads through DirectInput: with VirtualPad=1 it also lists one joystick,
// "XBOX 360 For Windows (Controller)", whose buttons and d-pad come from pad.txt as well.
static bool test_virtual_pad;
static const GUID TEST_PAD_GUID = {0x75a3c1e2, 0x1f4b, 0x4c6d, {0x9a, 0x10, 0x55, 0x41, 0x50, 0x41, 0x44, 0x30}};
static const GUID TEST_PAD_PRODUCT = {0x028E045E, 0x0000, 0x0000, {0x00, 0x00, 0x50, 0x49, 0x44, 0x56, 0x49, 0x44}};
static const char TEST_PAD_NAME[] = "XBOX 360 For Windows (Controller)";

static void TestPadInstance(DIDEVICEINSTANCEA *info) {
    DWORD size = info->dwSize ? info->dwSize : sizeof(*info);
    memset(info, 0, size);
    info->dwSize = size;
    info->guidInstance = TEST_PAD_GUID;
    info->guidProduct = TEST_PAD_PRODUCT;
    info->dwDevType = DI8DEVTYPE_GAMEPAD | (DI8DEVTYPEGAMEPAD_STANDARD << 8) | DIDEVTYPE_HID;
    strcpy_s(info->tszInstanceName, TEST_PAD_NAME);
    strcpy_s(info->tszProductName, TEST_PAD_NAME);
}

// Xbox 360 pad as DirectInput reports it: A B X Y LB RB Back Start LS RS = buttons 0-9.
static const WORD test_pad_di_buttons[] = {0x1000, 0x2000, 0x4000, 0x8000, 0x0100, 0x0200, 0x0020, 0x0010, 0x0040,
                                           0x0080};

// DirectInput object GUIDs (dxguid.lib is not linked).
#define TEST_DI_GUID(n) {0xA36D02E0 + n, 0xC9F3, 0x11CF, {0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00}}
static const GUID test_guid_x = TEST_DI_GUID(0x00), test_guid_y = TEST_DI_GUID(0x01), test_guid_z = TEST_DI_GUID(0x02), test_guid_rx = TEST_DI_GUID(0x14),
                  test_guid_ry = TEST_DI_GUID(0x15), test_guid_button = TEST_DI_GUID(0x10), test_guid_pov = TEST_DI_GUID(0x12);

class TestPadDevice : public IDirectInputDevice8A {
    LONG refs = 1;
    DIOBJECTDATAFORMAT objects[64] = {};
    DWORD object_count = 0, state_size = 0;
    LONG range_min = 0, range_max = 65535;

public:
    STDMETHOD(QueryInterface)(REFIID, void **out) { *out = this; AddRef(); return S_OK; }
    STDMETHOD_(ULONG, AddRef)() { return InterlockedIncrement(&refs); }
    STDMETHOD_(ULONG, Release)() { return InterlockedDecrement(&refs); }  // lives as long as the game
    STDMETHOD(GetCapabilities)(LPDIDEVCAPS caps) {
        DWORD size = caps->dwSize;
        memset(caps, 0, size);
        caps->dwSize = size;
        caps->dwFlags = DIDC_ATTACHED;
        caps->dwDevType = DI8DEVTYPE_GAMEPAD | (DI8DEVTYPEGAMEPAD_STANDARD << 8) | DIDEVTYPE_HID;
        caps->dwAxes = 5;
        caps->dwButtons = 10;
        caps->dwPOVs = 1;
        return DI_OK;
    }
    STDMETHOD(EnumObjects)(LPDIENUMDEVICEOBJECTSCALLBACKA callback, LPVOID ref, DWORD) {
        static const GUID *axes[] = {&test_guid_x, &test_guid_y, &test_guid_z, &test_guid_rx, &test_guid_ry};
        static const DWORD offsets[] = {DIJOFS_X, DIJOFS_Y, DIJOFS_Z, DIJOFS_RX, DIJOFS_RY};
        DIDEVICEOBJECTINSTANCEA o;
        for (DWORD i = 0; i < 16; ++i) {
            memset(&o, 0, sizeof(o));
            o.dwSize = sizeof(o);
            if (i < 5) {
                o.guidType = *axes[i]; o.dwOfs = offsets[i]; o.dwType = DIDFT_ABSAXIS | DIDFT_MAKEINSTANCE(i);
                sprintf_s(o.tszName, "Axis %lu", i);
            } else if (i < 15) {
                o.guidType = test_guid_button; o.dwOfs = DIJOFS_BUTTON(i - 5);
                o.dwType = DIDFT_PSHBUTTON | DIDFT_MAKEINSTANCE(i - 5);
                sprintf_s(o.tszName, "Button %lu", i - 5);
            } else {
                o.guidType = test_guid_pov; o.dwOfs = DIJOFS_POV(0); o.dwType = DIDFT_POV | DIDFT_MAKEINSTANCE(0);
                strcpy_s(o.tszName, "Hat Switch");
            }
            if (callback(&o, ref) == DIENUM_STOP) break;
        }
        return DI_OK;
    }
    STDMETHOD(GetProperty)(REFGUID property, LPDIPROPHEADER header) {
        if ((ULONG_PTR)&property == 4) {  // DIPROP_RANGE
            ((DIPROPRANGE *)header)->lMin = range_min;
            ((DIPROPRANGE *)header)->lMax = range_max;
            return DI_OK;
        }
        return DIERR_UNSUPPORTED;
    }
    STDMETHOD(SetProperty)(REFGUID property, LPCDIPROPHEADER header) {
        if ((ULONG_PTR)&property == 4) {  // DIPROP_RANGE
            range_min = ((const DIPROPRANGE *)header)->lMin;
            range_max = ((const DIPROPRANGE *)header)->lMax;
        }
        return DI_OK;
    }
    STDMETHOD(Acquire)() { return DI_OK; }
    STDMETHOD(Unacquire)() { return DI_OK; }
    STDMETHOD(GetDeviceState)(DWORD size, LPVOID data) {
        static LONG reads;
        if (InterlockedIncrement(&reads) == 1) Log("TEST PAD: the game reads the virtual joystick.");
        memset(data, 0, size);
        WORD pad = TestReadPad();
        DWORD button = 0, axis = 0;
        for (DWORD i = 0; i < object_count; ++i) {
            const DIOBJECTDATAFORMAT &f = objects[i];
            DWORD type = f.dwType, instance = DIDFT_GETINSTANCE(type);
            bool any = instance == (DIDFT_ANYINSTANCE >> 8);
            if (type & DIDFT_AXIS) {
                if (f.dwOfs + 4 <= size) *(LONG *)((BYTE *)data + f.dwOfs) = (range_min + range_max) / 2;
                ++axis;
            } else if (type & DIDFT_BUTTON) {
                DWORD n = any ? button : instance;
                ++button;
                if (f.dwOfs < size && n < 10 && (pad & test_pad_di_buttons[n])) ((BYTE *)data)[f.dwOfs] = 0x80;
            } else if (type & DIDFT_POV) {
                static const DWORD angle[16] = {0xFFFFFFFF, 0, 18000, 0xFFFFFFFF, 27000, 31500, 22500, 27000,
                                                9000, 4500, 13500, 9000, 0xFFFFFFFF, 0, 18000, 0xFFFFFFFF};
                if (f.dwOfs + 4 <= size) *(DWORD *)((BYTE *)data + f.dwOfs) = angle[pad & 15];
            }
        }
        return DI_OK;
    }
    STDMETHOD(GetDeviceData)(DWORD, LPDIDEVICEOBJECTDATA, LPDWORD count, DWORD) {
        if (count) *count = 0;
        return DI_OK;
    }
    STDMETHOD(SetDataFormat)(LPCDIDATAFORMAT format) {
        object_count = format->dwNumObjs < 64 ? format->dwNumObjs : 64;
        memcpy(objects, format->rgodf, object_count * sizeof(DIOBJECTDATAFORMAT));
        state_size = format->dwDataSize;
        return DI_OK;
    }
    STDMETHOD(SetEventNotification)(HANDLE) { return DI_OK; }
    STDMETHOD(SetCooperativeLevel)(HWND, DWORD) { return DI_OK; }
    STDMETHOD(GetObjectInfo)(LPDIDEVICEOBJECTINSTANCEA info, DWORD, DWORD) {
        DWORD size = info->dwSize;
        memset(info, 0, size);
        info->dwSize = size;
        return DI_OK;
    }
    STDMETHOD(GetDeviceInfo)(LPDIDEVICEINSTANCEA info) { TestPadInstance(info); return DI_OK; }
    STDMETHOD(RunControlPanel)(HWND, DWORD) { return DI_OK; }
    STDMETHOD(Initialize)(HINSTANCE, DWORD, REFGUID) { return DI_OK; }
    STDMETHOD(CreateEffect)(REFGUID, LPCDIEFFECT, LPDIRECTINPUTEFFECT *, LPUNKNOWN) { return DIERR_UNSUPPORTED; }
    STDMETHOD(EnumEffects)(LPDIENUMEFFECTSCALLBACKA, LPVOID, DWORD) { return DI_OK; }
    STDMETHOD(GetEffectInfo)(LPDIEFFECTINFOA, REFGUID) { return DIERR_UNSUPPORTED; }
    STDMETHOD(GetForceFeedbackState)(LPDWORD) { return DIERR_UNSUPPORTED; }
    STDMETHOD(SendForceFeedbackCommand)(DWORD) { return DIERR_UNSUPPORTED; }
    STDMETHOD(EnumCreatedEffectObjects)(LPDIENUMCREATEDEFFECTOBJECTSCALLBACK, LPVOID, DWORD) { return DI_OK; }
    STDMETHOD(Escape)(LPDIEFFESCAPE) { return DIERR_UNSUPPORTED; }
    STDMETHOD(Poll)() { return DI_OK; }
    STDMETHOD(SendDeviceData)(DWORD, LPCDIDEVICEOBJECTDATA, LPDWORD, DWORD) { return DI_OK; }
    STDMETHOD(EnumEffectsInFile)(LPCSTR, LPDIENUMEFFECTSINFILECALLBACK, LPVOID, DWORD) { return DIERR_UNSUPPORTED; }
    STDMETHOD(WriteEffectToFile)(LPCSTR, DWORD, LPDIFILEEFFECT, DWORD) { return DIERR_UNSUPPORTED; }
    STDMETHOD(BuildActionMap)(LPDIACTIONFORMATA, LPCSTR, DWORD) { return DIERR_UNSUPPORTED; }
    STDMETHOD(SetActionMap)(LPDIACTIONFORMATA, LPCSTR, DWORD) { return DIERR_UNSUPPORTED; }
    STDMETHOD(GetImageInfo)(LPDIDEVICEIMAGEINFOHEADERA) { return DIERR_UNSUPPORTED; }
};
static TestPadDevice *test_pad_device;

// The engine treats a DirectInput pad as an XInput pad only when WMI reports "IG_" in its
// device ID (function 0x518560, called with the product GUID). The virtual joystick has no
// such device, so in test mode the check is: product GUID = Xbox 360 pad (VID 045E, PID 028E).
#define RVA_IS_XINPUT_DEVICE 0x118560
static const BYTE expect_is_xinput[] = {0x81, 0xEC, 0x84, 0x00, 0x00, 0x00, 0x53, 0x56, 0x57, 0x33, 0xDB,
                                        0x6A, 0x4C, 0x8D, 0x44, 0x24, 0x48};
static const BYTE is_xinput_by_product[] = {
    0x8B, 0x44, 0x24, 0x04,              // mov eax, [esp+4]
    0x81, 0x38, 0x5E, 0x04, 0x8E, 0x02,  // cmp dword [eax], 0x028E045E
    0x0F, 0x94, 0xC0,                    // sete al
    0x0F, 0xB6, 0xC0,                    // movzx eax, al
    0xC3};                               // ret

static bool TestPadAsXInput() {
    BYTE *site = (BYTE *)GetModuleHandleW(NULL) + RVA_IS_XINPUT_DEVICE;
    if (memcmp(site, expect_is_xinput, sizeof(expect_is_xinput)) != 0) return false;
    DWORD old;
    if (!VirtualProtect(site, sizeof(is_xinput_by_product), PAGE_EXECUTE_READWRITE, &old)) return false;
    memcpy(site, is_xinput_by_product, sizeof(is_xinput_by_product));
    VirtualProtect(site, sizeof(is_xinput_by_product), old, &old);
    FlushInstructionCache(GetCurrentProcess(), site, sizeof(is_xinput_by_product));
    return true;
}

#define TEST_DI_VTABLE_ENUM_DEVICES 4
#define TEST_DI_VTABLE_DEVICE_STATUS 5
typedef HRESULT(STDMETHODCALLTYPE *DiEnumDevices_t)(void *, DWORD, LPDIENUMDEVICESCALLBACKA, LPVOID, DWORD);
typedef HRESULT(STDMETHODCALLTYPE *DiDeviceStatus_t)(void *, REFGUID);
static DiEnumDevices_t test_real_enum_devices;
static DiDeviceStatus_t test_real_device_status;

static HRESULT STDMETHODCALLTYPE TestEnumDevices(void *di, DWORD type, LPDIENUMDEVICESCALLBACKA callback, LPVOID ref,
                                                 DWORD flags) {
    HRESULT hr = test_real_enum_devices(di, type, callback, ref, flags);
    if (type == DI8DEVCLASS_ALL || type == DI8DEVCLASS_GAMECTRL || type == DI8DEVTYPE_GAMEPAD ||
        type == DI8DEVTYPE_JOYSTICK) {
        DIDEVICEINSTANCEA info = {sizeof(info)};
        TestPadInstance(&info);
        callback(&info, ref);
    }
    return hr;
}

static HRESULT STDMETHODCALLTYPE TestDeviceStatus(void *di, REFGUID guid) {
    return IsEqualGUID(guid, TEST_PAD_GUID) ? DI_OK : test_real_device_status(di, guid);
}

static HRESULT STDMETHODCALLTYPE TestDiCreateDevice(void *di, REFGUID guid, void **out, IUnknown *outer) {
    if (test_virtual_pad && out && IsEqualGUID(guid, TEST_PAD_GUID)) {
        if (!test_pad_device) test_pad_device = new TestPadDevice();
        test_pad_device->AddRef();
        *out = test_pad_device;
        Log("TEST PAD: virtual joystick created.");
        return DI_OK;
    }
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
    if (SUCCEEDED(hr) && out && *out) {
        TestPatchVtable(*(void ***)*out, TEST_DI_VTABLE_CREATE_DEVICE, (void *)&TestDiCreateDevice,
                        (void **)&test_real_di_create_device);
        if (test_virtual_pad && iid.Data1 == 0xBF798030) {  // IID_IDirectInput8A: the pad device is ANSI
            TestPatchVtable(*(void ***)*out, TEST_DI_VTABLE_ENUM_DEVICES, (void *)&TestEnumDevices,
                            (void **)&test_real_enum_devices);
            TestPatchVtable(*(void ***)*out, TEST_DI_VTABLE_DEVICE_STATUS, (void *)&TestDeviceStatus,
                            (void **)&test_real_device_status);
        }
    }
    return hr;
}

// Replaces an import of the game EXE taken by ordinal; returns the previous function or NULL.
static void *TestPatchOrdinal(const char *dll, WORD ordinal, void *replacement) {
    BYTE *base = (BYTE *)GetModuleHandleW(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY &dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress) return NULL;
    for (IMAGE_IMPORT_DESCRIPTOR *imp = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress); imp->Name; ++imp) {
        if (_stricmp((char *)(base + imp->Name), dll) != 0) continue;
        IMAGE_THUNK_DATA *thunk = (IMAGE_THUNK_DATA *)(base + imp->FirstThunk);
        IMAGE_THUNK_DATA *orig = (IMAGE_THUNK_DATA *)(base + (imp->OriginalFirstThunk ? imp->OriginalFirstThunk : imp->FirstThunk));
        for (; orig->u1.AddressOfData; ++orig, ++thunk) {
            if (!IMAGE_SNAP_BY_ORDINAL(orig->u1.Ordinal) || IMAGE_ORDINAL(orig->u1.Ordinal) != ordinal) continue;
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
    if (GetPrivateProfileIntW(L"Test", L"VirtualPad", 0, ini) != 0) {
        test_virtual_pad = true;
        Log(TestPadAsXInput() ? "TEST PAD: the virtual joystick counts as an XInput pad."
                              : "TEST PAD: unexpected XInput device check bytes; not patched.");
        test_real_xinput_state = (XInputGetState_t)TestPatchOrdinal("xinput1_3.dll", 2, (void *)&TestXInputState);
        test_real_xinput_caps = (XInputGetCaps_t)TestPatchOrdinal("xinput1_3.dll", 4, (void *)&TestXInputCaps);
        sprintf_s(message, "TEST PAD: XInputGetState hook %s, XInputGetCapabilities hook %s (scripts/screens/pad.txt).",
                  test_real_xinput_state ? "installed" : "NOT installed",
                  test_real_xinput_caps ? "installed" : "NOT installed");
        Log(message);
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
