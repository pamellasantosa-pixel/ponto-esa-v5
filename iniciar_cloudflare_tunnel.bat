@echo off
echo ========================================
echo  Iniciando Cloudflare Tunnel
echo  Aplicacao: http://localhost:8504
echo ========================================
echo.
echo Certifique-se que o Streamlit esta rodando na porta 8504!
echo.
echo Aguarde... gerando link publico gratuito...
echo.

cd /d "%~dp0"

"C:\Users\lf\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" tunnel --url http://localhost:8504 --protocol http2

echo.
echo Tunel encerrado!
pause
