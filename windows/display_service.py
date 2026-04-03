"""Windows display enumeration and rotation via Win32 API (ctypes)."""

import ctypes
import ctypes.wintypes as wintypes
import logging

logger = logging.getLogger(__name__)

# Constants
ENUM_CURRENT_SETTINGS = -1
CDS_UPDATEREGISTRY = 0x01
CDS_RESET = 0x40000000
DISP_CHANGE_SUCCESSFUL = 0
DISPLAY_DEVICE_ACTIVE = 0x00000001
DM_DISPLAYORIENTATION = 0x00000080
DM_PELSWIDTH = 0x00080000
DM_PELSHEIGHT = 0x00100000

DMDO_DEFAULT = 0  # 0°
DMDO_90 = 1       # 90°
DMDO_180 = 2      # 180°
DMDO_270 = 3      # 270°

ANGLE_TO_DMDO = {"0": DMDO_DEFAULT, "90": DMDO_90, "180": DMDO_180, "270": DMDO_270}
DMDO_TO_ANGLE = {v: k for k, v in ANGLE_TO_DMDO.items()}


class DEVMODE(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", ctypes.c_short),
        ("dmPaperSize", ctypes.c_short),
        ("dmPaperLength", ctypes.c_short),
        ("dmPaperWidth", ctypes.c_short),
        ("dmScale", ctypes.c_short),
        ("dmCopies", ctypes.c_short),
        ("dmDefaultSource", ctypes.c_short),
        ("dmPrintQuality", ctypes.c_short),
        ("dmPositionX", ctypes.c_long),
        ("dmPositionY", ctypes.c_long),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None


class DisplayService:

    @staticmethod
    def list_displays():
        """Enumerate active displays using Win32 API."""
        if user32 is None:
            logger.error("Win32 API not available (not running on Windows)")
            return []

        displays = []
        i = 0
        while True:
            dd = DISPLAY_DEVICE()
            dd.cb = ctypes.sizeof(dd)
            if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
                break
            i += 1

            if not (dd.StateFlags & DISPLAY_DEVICE_ACTIVE):
                continue

            devmode = DEVMODE()
            devmode.dmSize = ctypes.sizeof(devmode)
            if not user32.EnumDisplaySettingsW(dd.DeviceName, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode)):
                continue

            orientation = devmode.dmDisplayOrientation
            width = devmode.dmPelsWidth
            height = devmode.dmPelsHeight

            display = {
                "name": dd.DeviceName.rstrip("\x00"),
                "adapter": dd.DeviceString.rstrip("\x00"),
                "width": width,
                "height": height,
                "orientation": orientation,
                "orientation_degrees": DMDO_TO_ANGLE.get(orientation, "0"),
                "desc": f"{dd.DeviceName.strip(chr(0))} ({width}x{height}) - {dd.DeviceString.strip(chr(0))}",
            }
            displays.append(display)
            logger.info(f"Found display: {display['desc']} orientation={orientation}")

        logger.info(f"Total active displays: {len(displays)}")
        return displays

    @staticmethod
    def rotate_display(device_name, angle):
        """Rotate a display to the given angle (0, 90, 180, 270)."""
        if user32 is None:
            logger.error("Win32 API not available")
            return False

        if angle not in ANGLE_TO_DMDO:
            logger.error(f"Invalid angle: {angle}")
            return False

        new_orientation = ANGLE_TO_DMDO[angle]

        devmode = DEVMODE()
        devmode.dmSize = ctypes.sizeof(devmode)
        if not user32.EnumDisplaySettingsW(device_name, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode)):
            logger.error(f"Failed to get display settings for {device_name}")
            return False

        current_orientation = devmode.dmDisplayOrientation
        logger.info(f"Rotating {device_name}: {DMDO_TO_ANGLE.get(current_orientation)}° → {angle}°")

        # Swap width/height when switching between landscape and portrait
        current_is_landscape = current_orientation in (DMDO_DEFAULT, DMDO_180)
        new_is_landscape = new_orientation in (DMDO_DEFAULT, DMDO_180)
        if current_is_landscape != new_is_landscape:
            devmode.dmPelsWidth, devmode.dmPelsHeight = devmode.dmPelsHeight, devmode.dmPelsWidth
            logger.info(f"Swapped resolution to {devmode.dmPelsWidth}x{devmode.dmPelsHeight}")

        devmode.dmDisplayOrientation = new_orientation
        devmode.dmFields = DM_DISPLAYORIENTATION | DM_PELSWIDTH | DM_PELSHEIGHT

        result = user32.ChangeDisplaySettingsExW(
            device_name, ctypes.byref(devmode), None,
            CDS_UPDATEREGISTRY | CDS_RESET, None
        )

        if result == DISP_CHANGE_SUCCESSFUL:
            logger.info(f"Rotation successful: {device_name} → {angle}°")
            return True
        else:
            logger.error(f"ChangeDisplaySettingsEx failed with code {result}")
            return False
