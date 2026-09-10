@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo   Creating Desktop Shortcut for StickerFlow
echo ==================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$shortcutPath = [IO.Path]::Combine($desktop, 'StickerFlow.lnk'); " ^
  "$shortcut = $ws.CreateShortcut($shortcutPath); " ^
  "$shortcut.TargetPath = '%~dp0run.bat'; " ^
  "$shortcut.WorkingDirectory = '%~dp0'; " ^
  "$shortcut.Description = 'StickerFlow - WhatsApp Sticker Studio'; " ^
  "$shortcut.Save()"

if errorlevel 1 (
    echo [ERROR] Could not create desktop shortcut.
) else (
    echo [SUCCESS] StickerFlow shortcut created on your Desktop!
)
echo.
pause
