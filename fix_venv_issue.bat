@echo off
echo Fixing Windows virtual environment issue...
echo.

cd backend

echo Removing problematic lib64 symlink...
if exist "venv\lib64" (
    rmdir /s /q "venv\lib64" 2>nul
    echo ✅ Removed lib64 symlink
) else (
    echo ✅ No lib64 symlink found
)

echo.
echo Virtual environment fixed! You can now run the startup script.
echo.
pause
