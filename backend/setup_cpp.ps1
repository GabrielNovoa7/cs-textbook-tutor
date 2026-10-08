$ErrorActionPreference = 'Stop'
$compilerVersion = '0.15.2'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$compilerDirectory = Join-Path $projectDirectory '.tools'
$installedCompiler = Join-Path $compilerDirectory "zig-x86_64-windows-$compilerVersion\zig.exe"
if (Test-Path -LiteralPath $installedCompiler) { Write-Output 'Local C++ compiler is already installed.'; exit 0 }
New-Item -ItemType Directory -Force -Path $compilerDirectory | Out-Null
$downloadIndex = Invoke-RestMethod 'https://ziglang.org/download/index.json'
$compilerRelease = $downloadIndex.$compilerVersion.'x86_64-windows'
if (-not $compilerRelease) { throw 'Pinned compiler release was not found.' }
$compilerArchive = Join-Path $compilerDirectory 'zig-compiler.zip'
Invoke-WebRequest -Uri $compilerRelease.tarball -OutFile $compilerArchive
$actualChecksum = (Get-FileHash -LiteralPath $compilerArchive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualChecksum -ne $compilerRelease.shasum) { throw 'Compiler checksum did not match the official release.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$compilerZip = [System.IO.Compression.ZipFile]::OpenRead($compilerArchive)
try {
    foreach ($compilerEntry in $compilerZip.Entries) {
        $entryDestination = [System.IO.Path]::GetFullPath((Join-Path $compilerDirectory $compilerEntry.FullName))
        if (-not $entryDestination.StartsWith($compilerDirectory + [System.IO.Path]::DirectorySeparatorChar)) { throw 'Invalid compiler archive path.' }
        if ($compilerEntry.Name) {
            [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($entryDestination)) | Out-Null
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($compilerEntry, $entryDestination, $true)
        }
    }
} finally { $compilerZip.Dispose() }
Remove-Item -LiteralPath $compilerArchive
Write-Output 'Local C++ compiler installed and SHA256 verified.'
