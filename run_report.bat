@echo off
chcp 65001 >nul
title "KM&CO Automated Macro Report"
cd /d "D:\trading\News Last 48H"

echo =====================================================
echo   Lancement du pipeline macro-eco (KM&CO Desk)
echo =====================================================
echo.

rem =====================================================
rem [1/5]  Collecte des flux RSS et génération d'articles
rem =====================================================
echo [1/5] Collecte des flux RSS en cours...
"src\dist\news48_dump.exe" ^
  --config "D:\trading\News Last 48H\configs\sources.yaml" ^
  --outdir "D:\trading\News Last 48H\out" ^
  --hours 96 ^
  --keep-history
echo.

rem =====================================================
rem [2/5]  Génération automatique du rapport GLOBAL (IA Core)
rem =====================================================
echo [2/5] Génération automatique du rapport principal (report_global.md)...
python "ai_core\ai_generate_report.py"
echo.

rem =====================================================
rem [3/5]  Compilation du rapport institutionnel GLOBAL (.docx)
rem =====================================================
echo [3/5] Compilation du rapport institutionnel principal (.docx)...
python "src\generate_desk_report.py" --md "KMCO_out\report_global.md"
echo.

rem =====================================================
rem [4/5]  Génération automatique du rapport OVERNIGHT (IA Overnight Core)
rem =====================================================
echo [4/5] Génération automatique du rapport overnight (report_overnight.md)...
python "ai_core\ai_overnight_core\ai_generate_overnight.py"
echo.

rem =====================================================
rem [5/5]  Compilation du rapport OVERNIGHT (.docx)
rem =====================================================
echo [5/5] Compilation du rapport overnight (.docx)...
python "src\generate_desk_report.py" --md "KMCO_out\report_overnight.md"
echo.

echo =====================================================
echo   Tous les rapports ont été générés avec succès.
echo   -> Dossier : D:\trading\News Last 48H\KMCO_out
echo   -> Fichiers :
echo        - KMCO_Global_Macro_Report_[date].docx
echo        - KMCO_Overnight_Macro_Check_[date].docx
echo =====================================================

pause
