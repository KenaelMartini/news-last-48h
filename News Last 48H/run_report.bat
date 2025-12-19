@echo off
chcp 65001 >nul
title "KM^&CO Automated Macro Report"
cd /d "D:\trading\News Last 48H"

echo =====================================================
echo   Lancement du pipeline macro-eco (KM^&CO Desk)
echo =====================================================
echo.

rem 1. Scraper les flux RSS et générer articles.json
echo [1/3] Collecte des flux RSS en cours...
"src\dist\news48_dump.exe" ^
  --config "D:\trading\News Last 48H\configs\sources.yaml" ^
  --out "D:\trading\News Last 48H\out" ^
  --keep-history
echo.

rem 2. Générer le rapport markdown à partir des articles
echo [2/3] Génération du rapport intermédiaire (report.md)...
"src\dist\generate_report.exe" ^
  --articles "D:\trading\News Last 48H\out\articles.json" ^
  --outdir "D:\trading\News Last 48H\out"
echo.

rem 3. Construire le rapport Word institutionnel
echo [3/3] Compilation du rapport institutionnel (.docx)...
python "src\generate_desk_report.py"
echo.

echo =====================================================
echo   Rapport complet généré avec succès.
echo   -> Dossier : D:\trading\News Last 48H\out
echo   -> Fichier : KMCO_Global_Macro_Report_[date].docx
echo =====================================================

pause
