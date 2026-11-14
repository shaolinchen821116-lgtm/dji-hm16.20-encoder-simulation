@echo off
setlocal
cd /d "%~dp0"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe" "HM-16.20\build\HM_vc2015.sln" /t:TAppEncoder,TAppDecoder /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v145 /m:2 /v:minimal /nologo
if errorlevel 1 exit /b 1
if not exist "bin" mkdir "bin"
copy /y "HM-16.20\bin\vc2015\x64\Release\TAppEncoder.exe" "bin\TAppEncoder_pocket4.exe" > nul
if errorlevel 1 exit /b 1
copy /y "HM-16.20\bin\vc2015\x64\Release\TAppDecoder.exe" "bin\TAppDecoder_pocket4.exe" > nul
exit /b %errorlevel%
