$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $projectRoot 'original/source_manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sourcePath = Join-Path $projectRoot $manifest.source.path
$sourceItem = Get-Item -LiteralPath $sourcePath
if ($sourceItem.Length -ne $manifest.source.size_bytes) { throw 'Source ISO size mismatch.' }
$actualHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
if ($actualHash -ne $manifest.source.sha256) { throw 'Source ISO SHA-256 mismatch.' }
Write-Output "PASS: Source ISO size and SHA-256 match."
Write-Output $actualHash
