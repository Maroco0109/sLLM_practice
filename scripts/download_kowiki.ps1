param(
  [string]$Project = "kowiki",
  [string]$OutDir = "data/raw"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Get-LatestDumpDate([string]$project) {
  $index = Invoke-WebRequest -UseBasicParsing -Uri "https://dumps.wikimedia.org/$project/"
  $dates = @()
  foreach ($l in $index.Links) {
    if ($l.href -match '^(\d{8})/$') { $dates += [int]$Matches[1] }
  }
  if ($dates.Count -eq 0) { throw "No dump dates found for $project" }
  return ($dates | Measure-Object -Maximum).Maximum
}

function Get-RemoteSize([string]$url) {
  $head = Invoke-WebRequest -Method Head -UseBasicParsing -Uri $url
  $len = $head.Headers['Content-Length']
  if ($len -is [array]) { $len = $len[0] }
  return [int64]$len
}

$date = Get-LatestDumpDate -project $Project
$fname = "$Project-$date-pages-articles.xml.bz2"
$url = "https://dumps.wikimedia.org/$Project/$date/$fname"
$outPath = Join-Path $OutDir $fname

$size = Get-RemoteSize -url $url
$gb = [Math]::Round($size / 1GB, 2)
Write-Host "Remote file:" $url
Write-Host "Size:" $gb "GB (" $size "bytes)"

if (Test-Path $outPath) {
  $local = (Get-Item $outPath).Length
  if ($local -eq $size) {
    Write-Host "Already downloaded:" $outPath
    exit 0
  } else {
    Write-Warning "Partial file detected ($local/$size bytes). Resuming..."
  }
}

Write-Host "Downloading to" $outPath "with resume support..."
Invoke-WebRequest -Uri $url -OutFile $outPath -Resume
Write-Host "Done." (Get-Item $outPath).Length "bytes saved."
