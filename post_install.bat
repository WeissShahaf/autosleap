echo off
powershell -Command "Invoke-WebRequest  https://github.com/StempelLab/sleap_well/blob/main/gui/half_logo.jpg -OutFile %CONDA_PREFIX%/Lib/site-packages/sleap/gui/logo.jpg"