# windows-install.ps1 -- the PowerShell inside windows-install.bat
# (tools/mkinstall.py puts it there; the .bat runs it with -File, passing its
# own path and the folder dropped on it). Windows PowerShell 5.1; ASCII
# only, as it reads a .ps1 without a byte-order mark as the ANSI code page.
#
# What linux-install.sh does: find the installed NOLF2 (the argument, or
# the InstallDir its setup wrote in the registry), check that the files the
# list at the end of the .bat names are there with the 1.3 sizes, then
# write each file of the list from its byte ranges -- C <source> <offset>
# <length>, Z <length> zeros, L <base64> -- check its size and SHA-256, and
# move it into place. The flags (opt, own, once) are tools/mkinstall.py's.
param(
    [Parameter(Mandatory = $true)][string]$Self,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Dirs
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $Self

# Any other error: say it.
trap {
    Write-Host ''
    Write-Host "windows-install: $_" -ForegroundColor Red
    if ($out) { $out.Close() }
    if ($streams) { foreach ($s in $streams.Values) { $s.Close() } }
    exit 1
}

function Fail($msg) {
    Write-Host ''
    Write-Host "windows-install: $msg" -ForegroundColor Red
    exit 1
}

function Get-Sha256($path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

# The list: every line after the marker line.
$text = [IO.File]::ReadAllText($Self)
$marker = '__NOLF2_INSTALL' + '_DATA__'
$at = $text.IndexOf("`n" + $marker)
if ($at -lt 0) { Fail 'the file list is missing from the .bat' }
$lines = $text.Substring($at + 1 + $marker.Length) -split "`r?`n" | Where-Object { $_ -ne '' }

# The installed game: the folder given, or where setup said it put it.
$src = $null
if ($Dirs -and $Dirs.Count -gt 0) {
    $src = $Dirs[0]
} else {
    foreach ($key in 'HKLM:\SOFTWARE\WOW6432Node\Monolith Productions\No One Lives Forever 2\1.0',
                     'HKLM:\SOFTWARE\Monolith Productions\No One Lives Forever 2\1.0') {
        $v = Get-ItemProperty -LiteralPath $key -Name InstallDir -ErrorAction SilentlyContinue
        if ($v -and $v.InstallDir -and (Test-Path -LiteralPath $v.InstallDir -PathType Container)) {
            $src = $v.InstallDir
            break
        }
    }
    if (-not $src) { Fail 'NOLF2 is not in the registry: drop the folder you installed it in onto windows-install.bat' }
}
if (-not (Test-Path -LiteralPath $src -PathType Container)) { Fail "$src`: no such folder" }
$src = (Resolve-Path -LiteralPath $src).ProviderPath
if ($src.TrimEnd('\', '/') -eq $here.TrimEnd('\', '/')) { Fail "$src is this folder; give your installed NOLF2" }
Write-Host "installing from $src"

# The sources: each file of the install the list uses, found and of the
# right size (a wrong version of the game fails here, before anything is
# written). Only the Microsoft runtime (opt) may be missing or another
# version, and the settings (own) another size.
$sources = @{}
$bad = $false
foreach ($l in $lines) {
    if (-not $l.StartsWith('S ')) { continue }
    $p = $l.Split(' ', 6)
    $path = Join-Path $src ($p[5].Replace('/', [IO.Path]::DirectorySeparatorChar))
    $s = @{ Size = [int64]$p[2]; Kind = $p[4]; Name = $p[5]; Path = $null }
    $sources[$p[1]] = $s
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        if ($s.Kind -ne 'opt') { Write-Host "no $($s.Name) in $src" -ForegroundColor Red; $bad = $true }
        continue
    }
    $s.Path = $path
    $len = ([IO.FileInfo]$path).Length
    if ($s.Kind -eq '-' -and $len -ne $s.Size) {
        Write-Host "$path is not the 1.3 one ($len bytes, not $($s.Size))" -ForegroundColor Red
        $bad = $true
    }
}
if ($bad) { Fail 'that is not NOLF2 updated to 1.3 (English); see the top of windows-install.bat' }

function Test-Done($path, $size, $sha) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
    if (([IO.FileInfo]$path).Length -ne $size) { return $false }
    return (Get-Sha256 $path) -eq $sha
}

function Open-Source($n) {
    if (-not $streams.ContainsKey($n)) { $streams[$n] = [IO.File]::OpenRead($sources[$n].Path) }
    return $streams[$n]
}

$streams = @{}
$buf = New-Object byte[] (1MB)
$zero = New-Object byte[] (1MB)
$out = $null
$written = 0
$kept = 0
$skipped = 0
$skip = $true
$whole = $null
try {
    foreach ($l in $lines) {
        $p = $l.Split(' ')
        switch ($p[0]) {
            'F' {
                $name = $p[1]
                $dest = Join-Path $here ($name.Replace('/', [IO.Path]::DirectorySeparatorChar))
                $size = [int64]$p[2]
                $sha = $p[3]
                $flag = $p[4]
                $part = "$dest.part"
                $whole = $null
                $skip = (($flag -eq 'once') -and (Test-Path -LiteralPath $dest)) -or (Test-Done $dest $size $sha)
                if ($skip) { $kept++ } else {
                    Write-Host $name
                    $dir = Split-Path -Parent $dest
                    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
                    $out = [IO.File]::Create($part)
                }
            }
            'C' {
                if ($skip -or $whole) { continue }
                $s = $sources[$p[1]]
                if (-not $s.Path -or ([IO.FileInfo]$s.Path).Length -ne $s.Size) {
                    if ($flag -eq 'opt') {
                        Write-Host '  not in that folder, or another version: skipped (Windows has its own)'
                        $out.Close(); $out = $null
                        Remove-Item -LiteralPath $part -Force
                        $skip = $true
                        $skipped++
                        continue
                    }
                    if ($flag -eq 'own' -or $flag -eq 'once') { $whole = $s.Path; continue }
                    Fail "$($s.Name): missing or the wrong size"
                }
                $in = Open-Source $p[1]
                $in.Position = [int64]$p[2]
                $left = [int64]$p[3]
                while ($left -gt 0) {
                    $n = $in.Read($buf, 0, [int][Math]::Min($left, [int64]$buf.Length))
                    if ($n -le 0) { Fail "$($s.Name) ended early" }
                    $out.Write($buf, 0, $n)
                    $left -= $n
                }
            }
            'Z' {
                if ($skip -or $whole) { continue }
                $left = [int64]$p[1]
                while ($left -gt 0) {
                    $n = [int][Math]::Min($left, [int64]$zero.Length)
                    $out.Write($zero, 0, $n)
                    $left -= $n
                }
            }
            'L' {
                if ($skip -or $whole) { continue }
                $b = [Convert]::FromBase64String($p[1])
                $out.Write($b, 0, $b.Length)
            }
            'E' {
                if ($skip) { continue }
                $out.Close()
                $out = $null
                if ($whole) { Copy-Item -LiteralPath $whole -Destination $part -Force }
                if (-not (Test-Done $part $size $sha)) {
                    if ($flag -eq 'opt') {
                        Write-Host '  another version in that folder: skipped (Windows has its own)'
                        Remove-Item -LiteralPath $part -Force
                        $skipped++
                        continue
                    }
                    if ($flag -eq 'own' -or $flag -eq 'once') {
                        Write-Host '  not the shipped one: your own settings, taken as they are'
                    } else {
                        Remove-Item -LiteralPath $part -Force
                        Fail "$name came out wrong (not the 1.3 file, or a disk error?); the files before it are in place"
                    }
                }
                Move-Item -LiteralPath $part -Destination $dest -Force
                $written++
            }
        }
    }
} finally {
    if ($out) { $out.Close() }
    foreach ($s in $streams.Values) { $s.Close() }
}
$save = Join-Path $here 'Save'
if (-not (Test-Path -LiteralPath $save)) { New-Item -ItemType Directory -Path $save | Out-Null }
$note = ''
if ($skipped) { $note = ", $skipped skipped" }
Write-Host ''
Write-Host "done: $written files written, $kept already in place$note." -ForegroundColor Green
Write-Host 'Start the game from this folder: Lithtech.exe -cmdfile nolf2cmds.txt' -ForegroundColor Green
exit 0
