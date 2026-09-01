@echo off

cd /d "%~dp0"

echo ============================================
echo TENNIS EDGE PRO
echo ACTUALIZANDO Y ENTRENANDO
echo ============================================

py -3.12 update_and_train.py

echo.
echo ============================================
echo PROCESO TERMINADO
echo ============================================

pause