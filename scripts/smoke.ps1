$ErrorActionPreference = "Stop"

$apiBase = if ($env:DOCPILOT_API_BASE) {
    $env:DOCPILOT_API_BASE.TrimEnd("/")
} else {
    "http://127.0.0.1:8000"
}
$repoRoot = Split-Path -Parent $PSScriptRoot
$samplePath = Join-Path $repoRoot "sample-data\refund-policy.md"

function Invoke-DocPilotJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [object]$Body
    )

    $parameters = @{
        Method = $Method
        Uri = "$apiBase$Path"
        UseBasicParsing = $true
    }
    if ($null -ne $Body) {
        $parameters.ContentType = "application/json; charset=utf-8"
        $parameters.Body = $Body | ConvertTo-Json -Depth 10 -Compress
    }
    Invoke-RestMethod @parameters
}

function Upload-DocPilotFile {
    param(
        [Parameter(Mandatory = $true)][string]$KnowledgeBaseId,
        [Parameter(Mandatory = $true)][string]$FilePath
    )

    Add-Type -AssemblyName System.Net.Http
    $client = New-Object System.Net.Http.HttpClient
    $form = New-Object System.Net.Http.MultipartFormDataContent
    try {
        $bytes = [System.IO.File]::ReadAllBytes($FilePath)
        $fileContent = New-Object System.Net.Http.ByteArrayContent -ArgumentList @(,$bytes)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("text/markdown")
        $form.Add($fileContent, "file", [System.IO.Path]::GetFileName($FilePath))
        $response = $client.PostAsync("$apiBase/api/knowledge-bases/$KnowledgeBaseId/documents", $form).GetAwaiter().GetResult()
        $payload = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "File upload failed: HTTP $([int]$response.StatusCode) $payload"
        }
        $payload | ConvertFrom-Json
    } finally {
        $form.Dispose()
        $client.Dispose()
    }
}

Write-Host "[1/5] Check API health"
$health = Invoke-DocPilotJson -Method Get -Path "/api/health"
if ($health.status -ne "ok" -or $health.database -ne "ok") {
    throw "API health check failed"
}
if ($health.models -ne "configured") {
    throw "Bailian is not configured. Set BAILIAN_API_KEY in .env."
}

if (-not (Test-Path -LiteralPath $samplePath)) {
    throw "Acceptance sample is missing: $samplePath"
}

Write-Host "[2/5] Create a temporary knowledge base and upload a sample"
$knowledgeBase = Invoke-DocPilotJson -Method Post -Path "/api/knowledge-bases" -Body @{
    name = "smoke-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
    description = "Real-service acceptance data created by smoke.ps1"
}
$document = Upload-DocPilotFile -KnowledgeBaseId $knowledgeBase.id -FilePath $samplePath

Write-Host "[3/5] Process the document and verify chunks"
$processed = Invoke-DocPilotJson -Method Post -Path "/api/documents/$($document.id)/process"
if ($processed.status -ne "ready" -or [int]$processed.chunk_count -lt 1) {
    throw "The document is not ready or contains no chunks"
}

Write-Host "[4/5] Verify a grounded answer with citations"
$known = Invoke-DocPilotJson -Method Post -Path "/api/chat" -Body @{
    knowledge_base_id = $knowledgeBase.id
    question = "How many days after delivery can a refund request be submitted?"
    top_k = 5
    threshold = 0.7
}
if ($known.decision -ne "answer" -or $known.citations.Count -lt 1) {
    throw "The grounded question did not return a cited answer"
}

Write-Host "[5/5] Verify refusal for an unsupported question"
$unknown = Invoke-DocPilotJson -Method Post -Path "/api/chat" -Body @{
    knowledge_base_id = $knowledgeBase.id
    question = "What is tomorrow's lunch menu at the Mars base?"
    top_k = 5
    threshold = 0.7
}
if ($unknown.decision -ne "insufficient_context" -or $unknown.citations.Count -ne 0) {
    throw "The unsupported question was not refused"
}

Write-Host "DocPilot smoke test passed. Knowledge base: $($knowledgeBase.id)"
