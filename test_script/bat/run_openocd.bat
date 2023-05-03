echo "start to load bin file"

set build_path=%~1

cd %build_path%
cd load_bin

set openocd_dir=%~dp0\openocd

%openocd_dir%\openocd.exe -f jh8100.cfg
