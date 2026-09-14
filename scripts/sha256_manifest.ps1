param(
    [string]$Path = ".",
    [string]$OutFile = ".\SHA256SUMS.txt"
)

$resolvedOut = [System.IO.Path]::GetFullPath($OutFile)
$rows = Get-ChildItem -Path $Path -File -Recurse | Where-Object {
    [System.IO.Path]::GetFullPath($_.FullName) -ne $resolvedOut
} | ForEach-Object {
    $hash = Get-FileHash -Path $_.FullName -Algorithm SHA256
    "{0}  {1}" -f $hash.Hash.ToLower(), $_.FullName
}
$rows | Set-Content -Encoding ascii $OutFile
Write-Host "Wrote $OutFile"
