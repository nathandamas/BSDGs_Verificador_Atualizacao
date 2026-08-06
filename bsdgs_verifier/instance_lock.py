from __future__ import annotations

import os


class SingleInstanceGuard:
    """Impede múltiplas instâncias simultâneas da interface no Windows."""

    _MUTEX_NAME = r"Local\BSDGs_Verificador_Atualizacao_GUI_v1"
    _ERROR_ALREADY_EXISTS = 183

    def __init__(self) -> None:
        self._handle = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        kernel32.CreateMutexW.restype = wintypes.HANDLE

        handle = kernel32.CreateMutexW(None, False, self._MUTEX_NAME)
        if not handle:
            return True

        if ctypes.get_last_error() == self._ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None or os.name != "nt":
            return

        try:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(self._handle)
        finally:
            self._handle = None

    def __del__(self) -> None:
        try:
            self.release()
        except Exception:
            pass
