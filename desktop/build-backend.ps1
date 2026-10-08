$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoRoot
$runtimePath = Join-Path $repoRoot '.tools/python-runtime'
$runtimeZip = Join-Path $repoRoot '.tools/python-3.13.16-embed-amd64.zip'
if (!(Test-Path -LiteralPath "$runtimePath/python.exe")) {
    New-Item -ItemType Directory -Force -Path "$repoRoot/.tools" | Out-Null
    Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.16/python-3.13.16-embed-amd64.zip' -OutFile $runtimeZip
    $expected = '97dae5274cc54867065e8d5a3226e48c35017ed332a0fdb0e27d5b5821961297'
    if ((Get-FileHash -LiteralPath $runtimeZip -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'Python runtime checksum did not match.' }
    Expand-Archive -LiteralPath $runtimeZip -DestinationPath $runtimePath -Force
}
& "$repoRoot/backend/venv/Scripts/python.exe" -m PyInstaller --noconfirm --onedir --name tutor-backend --distpath desktop-build/backend --workpath desktop-build/pyinstaller --specpath desktop-build --paths $repoRoot --collect-all chromadb --collect-all onnxruntime --collect-all tokenizers --collect-all uvicorn backend/desktop_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Backend packaging failed.' }
Copy-Item -LiteralPath $runtimePath -Destination "$repoRoot/desktop-build/backend/tutor-backend/python-runtime" -Recurse -Force
Write-Output 'Bundled backend and Python exercise runtime are ready.'
