@echo off

set PKGDIR=packaging

rmdir /S /Q %PKGDIR%
mkdir %PKGDIR%
cd %PKGDIR%

cmake ..
cpack

copy *.zip ..

cd ..
rmdir /S /Q %PKGDIR%

@echo on
