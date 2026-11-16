$ErrorActionPreference = 'Stop'
$taskDirectory = [IO.Path]::GetFullPath($PSScriptRoot)
$fileName = 'qwen_image_2.1_fun_controlnet_union_int8_convrot.safetensors'
$sourcePath = [IO.Path]::GetFullPath((Join-Path $taskDirectory $fileName))
$modelDirectory = 'C:\Users\Administrator\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\model_patches'
$targetPath = [IO.Path]::GetFullPath((Join-Path $modelDirectory $fileName))
$expectedHash = '07aa961570ac0e03d4ca936aecd76854d077a33cde69b5092399afba01b3715d'
$expectedBytes = 3779298944

# Only this exact staged file may move into this exact model directory.
if ([IO.Path]::GetDirectoryName($sourcePath) -ne $taskDirectory -or
    [IO.Path]::GetDirectoryName($targetPath) -ne $modelDirectory) {
    throw 'Unexpected resolved installation path'
}
$staged = Get-Content -LiteralPath (Join-Path $taskDirectory 'staged.json') -Raw | ConvertFrom-Json
if ($staged.sha256 -ne $expectedHash -or $staged.size -ne $expectedBytes -or
    $staged.status -ne 'sha256_and_header_verified') { throw 'Staging verification does not match the requested model' }
$reused = Test-Path -LiteralPath $targetPath
if (-not $reused) {
    if ((Get-Item -LiteralPath $sourcePath).Length -ne $expectedBytes -or
        (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'Staged model verification failed; preserved'
    }
    if (-not (Test-Path -LiteralPath $modelDirectory)) {
        New-Item -ItemType Directory -Path $modelDirectory | Out-Null
    }
    Move-Item -LiteralPath $sourcePath -Destination $targetPath -ErrorAction Stop
}
if ((Get-Item -LiteralPath $targetPath).Length -ne $expectedBytes -or
    (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'Installed file does not match expected model; no existing file overwritten'
}
$receipt = [ordered]@{
    status = 'installed_and_sha256_verified'
    repository = $staged.repository
    revision = $staged.revision
    file = $staged.file
    destination = $targetPath
    bytes = $expectedBytes
    sha256 = $expectedHash
    reused_existing = $reused
    verified_utc = [DateTime]::UtcNow.ToString('o')
    changes = 'One model file; no ComfyUI source, dependencies, configuration or runtime changes'
}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskDirectory 'installed.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 5
