# Script para reconfigurar o Cloudflare Tunnel
# Execute como Administrador

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Reconfiguração do Cloudflare Tunnel" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se está rodando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERRO: Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "Clique com botão direito no arquivo e escolha 'Executar como Administrador'" -ForegroundColor Yellow
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Host "1. Parando serviço Cloudflared..." -ForegroundColor Yellow
Stop-Service -Name "Cloudflared" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "2. Desinstalando serviço antigo..." -ForegroundColor Yellow
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" service uninstall
Start-Sleep -Seconds 2

Write-Host "3. Reinstalando serviço com token..." -ForegroundColor Yellow
$token = "eyJhIjoiZWNmNTg1ZjA0ZDIzNTRhOWNlZWUwNjM0YjY3NGRmMGIiLCJ0IjoiYWM4Y2JhMTQtZmVjYi00ZDEwLTg1ZDktMDMyOTUxNzIwZjVmIiwicyI6IlkyUTFPVEV5WVdJdFkySXdPUzAwTkdaaUxUZ3hOR0V0T0RnNVpEUXdZbVJsTVRrMCJ9"
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" service install $token
Start-Sleep -Seconds 3

Write-Host "4. Iniciando serviço..." -ForegroundColor Yellow
Start-Service -Name "Cloudflared"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Configuração concluída!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Aguarde 1-2 minutos e teste:" -ForegroundColor Cyan
Write-Host "  https://sistemaponto.duckdns.org" -ForegroundColor White
Write-Host ""

Read-Host "Pressione Enter para fechar"
