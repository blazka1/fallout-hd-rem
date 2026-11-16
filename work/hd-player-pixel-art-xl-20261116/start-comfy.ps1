$ErrorActionPreference='Stop'
$taskComfyRoot='C:\Users\Administrator\AppData\Local\Comfy-Desktop\ComfyUI-Installs\local\ComfyUI'
$taskPython=Join-Path $taskComfyRoot '.venv/Scripts/python.exe'
$taskBase=Join-Path $PSScriptRoot 'comfy'
foreach($name in @('input','output','user','temp','cuda-cache','hf-cache','torch-cache')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $taskBase $name) | Out-Null
}
try { $null=Invoke-RestMethod 'http://127.0.0.1:8188/system_stats' -TimeoutSec 2; throw 'A ComfyUI server is already running; inspect its queue first.' }
catch { if($_.Exception.Message -like 'A ComfyUI server*'){throw} }
$env:PYTHONDONTWRITEBYTECODE='1'
$env:CUDA_CACHE_PATH=Join-Path $taskBase 'cuda-cache'
$env:HF_HOME=Join-Path $taskBase 'hf-cache'
$env:TORCH_HOME=Join-Path $taskBase 'torch-cache'
$taskArguments=@('main.py','--listen','127.0.0.1','--port','8188','--disable-auto-launch','--disable-all-custom-nodes',
    '--reserve-vram','1.5','--preview-method','none','--extra-model-paths-config',(Join-Path $PSScriptRoot 'models.yaml'),
    '--input-directory',(Join-Path $taskBase 'input'),'--output-directory',(Join-Path $taskBase 'output'),
    '--user-directory',(Join-Path $taskBase 'user'),'--temp-directory',(Join-Path $taskBase 'temp'))
$taskProcess=Start-Process -FilePath $taskPython -WorkingDirectory $taskComfyRoot -ArgumentList $taskArguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $PSScriptRoot 'comfy-stdout.log') -RedirectStandardError (Join-Path $PSScriptRoot 'comfy-stderr.log')
[pscustomobject]@{pid=$taskProcess.Id;python=$taskPython;started_utc=[DateTime]::UtcNow.ToString('o');arguments=$taskArguments} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'server.json') -Encoding UTF8
Write-Output "ComfyUI helper PID $($taskProcess.Id)"
