@echo off
setlocal
cd /d "%~dp0"
set "ADB=..\adb.exe"
if not exist "%ADB%" (
  echo ERROR: expected ..\adb.exe next to repository directory
  exit /b 1
)
if not exist "init_boot_a.img" (
  echo ERROR: init_boot_a.img missing in current directory
  exit /b 1
)
if not exist "mp\boot_patch.sh" (
  echo ERROR: run python scripts\extract_magisk_arm32.py Magisk-v30.7.apk first
  exit /b 1
)
if exist "magisk_patched_init_boot_a.img" (
  echo ERROR: magisk_patched_init_boot_a.img already exists; rename or remove it first.
  exit /b 1
)
"%ADB%" devices -l
if errorlevel 1 exit /b 1
"%ADB%" shell "mkdir -p /data/local/tmp/mp"
if errorlevel 1 exit /b 1
"%ADB%" push "mp" /data/local/tmp/
if errorlevel 1 exit /b 1
"%ADB%" push "init_boot_a.img" /data/local/tmp/mp/init_boot_a.img
if errorlevel 1 exit /b 1
"%ADB%" shell "chmod 755 /data/local/tmp/mp/busybox /data/local/tmp/mp/magiskboot /data/local/tmp/mp/magisk /data/local/tmp/mp/magiskinit /data/local/tmp/mp/init-ld"
if errorlevel 1 exit /b 1
"%ADB%" shell "cd /data/local/tmp/mp && ASH_STANDALONE=1 BOOTMODE=true KEEPVERITY=true KEEPFORCEENCRYPT=true RECOVERYMODE=false ./busybox sh ./boot_patch.sh ./init_boot_a.img && test -f new-boot.img && ls -l new-boot.img"
if errorlevel 1 (
 echo ERROR: boot_patch.sh failed. Nothing was flashed.
 exit /b 1
)
"%ADB%" pull /data/local/tmp/mp/new-boot.img magisk_patched_init_boot_a.img
if errorlevel 1 exit /b 1
python scripts\init_boot_inspect.py magisk_patched_init_boot_a.img
if errorlevel 1 exit /b 1
certutil -hashfile magisk_patched_init_boot_a.img SHA256
if errorlevel 1 exit /b 1
echo SUCCESS. Patched file: magisk_patched_init_boot_a.img
echo IMPORTANT: Do not flash until size/header/hash have been reviewed.
