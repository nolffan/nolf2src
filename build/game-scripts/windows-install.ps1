# windows-install.ps1 -- the PowerShell inside windows-install.bat
# (tools/mkinstall.py puts it there; the .bat runs it with -File, passing its
# own path and the files dropped on it). Windows PowerShell 5.1; ASCII
# only, as it reads a .ps1 without a byte-order mark as the ANSI code page.
#
# What linux-install.sh does: find the two disc images and the 1.3 update
# (the arguments, or the files in the game folder or the one above it; a
# redump .bin, .cue or .zip converted to a temporary .iso first), check
# their sizes and SHA-256, unpack the update's cabinet, then write each file
# of the list at the end of the .bat from the retail file it names -- read
# from byte ranges of the images, as they are or as InstallShield 6
# cabinet data (16-bit length, raw deflate stream; .NET's DeflateStream
# inflates them) -- by its records: C <length> its bytes, Z <length> zeros,
# L <base64> ours; check its size and SHA-256, and move it into place.
param(
    [Parameter(Mandatory = $true)][string]$Self,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Images
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $Self

# Converted images (.disc-<n>.iso.part), removed however the script ends.
$script:temps = @()
function Remove-Temps {
    foreach ($t in $script:temps) { Remove-Item -LiteralPath $t -Force -ErrorAction SilentlyContinue }
}

# Any other error: say it, and still remove the converted images.
trap {
    Write-Host ''
    Write-Host "windows-install: $_" -ForegroundColor Red
    if ($out) { $out.Close() }
    if ($streams) { foreach ($s in $streams.Values) { $s.Close() } }
    Remove-Temps
    exit 1
}

function Fail($msg) {
    Write-Host ''
    Write-Host "windows-install: $msg" -ForegroundColor Red
    Remove-Temps
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

# The images (D: a disc's .iso, U: the update), their redump .bin sizes (R)
# and the sets the game installs from (S <name> <id>...).
$imgs = @{}
$sets = @()
foreach ($l in $lines) {
    $p = $l.Split(' ')
    if ($p[0] -eq 'D' -or $p[0] -eq 'U') {
        $imgs[$p[1]] = @{ Size = [int64]$p[2]; Sha = $p[3]; Name = $l.Split(' ', 5)[4]; Raw = [int64]-1; Path = $null }
    } elseif ($p[0] -eq 'R') {
        $imgs[$p[1]].Raw = [int64]$p[2]
    } elseif ($p[0] -eq 'S') {
        $sets += , @($p[1..($p.Count - 1)])
    }
}
function Test-Complete {
    foreach ($s in $sets) {
        $ok = $true
        foreach ($id in $s[1..($s.Count - 1)]) { if (-not $imgs[$id].Path) { $ok = $false } }
        if ($ok) { return $true }
    }
    return $false
}

# A redump image: a .bin, or the one .bin of a .zip, of 2352-byte MODE1 or
# MODE2 sectors. Open-Raw gives @(size, stream) (stream $null with -SizeOnly);
# a .zip without exactly one .bin has size 0, so it matches no disc.
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Open-Raw($path, [switch]$SizeOnly) {
    if ($path.ToLowerInvariant().EndsWith('.zip')) {
        try { $zip = [IO.Compression.ZipFile]::OpenRead($path) } catch { return @([int64]0, $null) }
        $bins = @($zip.Entries | Where-Object { $_.FullName.ToLowerInvariant().EndsWith('.bin') })
        if ($bins.Count -ne 1) { $zip.Dispose(); return @([int64]0, $null) }
        if ($SizeOnly) { $size = $bins[0].Length; $zip.Dispose(); return @($size, $null) }
        return @($bins[0].Length, $bins[0].Open())
    }
    $size = ([IO.FileInfo]$path).Length
    if ($SizeOnly) { return @($size, $null) }
    return @($size, [IO.File]::OpenRead($path))
}

# The .iso of a redump image: the 2048 bytes of user data of each sector,
# after its 16-byte sync and header -- and, on a MODE2 track (the USA
# discs; the European ones are MODE1), its 8-byte subheader.
function Convert-Raw($path, $out) {
    $r = Open-Raw $path
    $src = $r[1]
    $dst = [IO.File]::Create($out)
    try {
        $S = 2352
        $buf = New-Object byte[] ($S * 512)
        $k = 0
        while ($true) {
            $have = 0
            while ($have -lt $buf.Length) {       # a zip stream can read short
                $n = $src.Read($buf, $have, $buf.Length - $have)
                if ($n -le 0) { break }
                $have += $n
            }
            if ($have -eq 0) { break }
            if ($have % $S) { Fail "$(Split-Path -Leaf $path): not whole 2352-byte sectors" }
            # the track's mode, as its first sector's header gives it
            if ($k -eq 0) { if ($buf[15] -eq 2) { $k = 24 } else { $k = 16 } }
            for ($i = 0; $i -lt $have; $i += $S) { $dst.Write($buf, $i + $k, 2048) }
            if ($have -lt $buf.Length) { break }
        }
    } finally {
        $dst.Close()
        $src.Close()
    }
}

# Which image a file is, if any: by size, then SHA-256 (computed once).
function Use-Image($path, $label) {
    $size = ([IO.FileInfo]$path).Length
    $sum = $null
    foreach ($id in @($imgs.Keys)) {
        $d = $imgs[$id]
        if ($d.Path -or $size -ne $d.Size) { continue }
        if (-not $sum) {
            Write-Host "checking $label ..."
            $sum = Get-Sha256 $path
        }
        if ($sum -eq $d.Sha) {
            $d.Path = $path
            Write-Host "  $($d.Name)"
            return $true
        }
    }
    if ($sum) { Write-Host '  the size of an image, but not its contents (a bad copy?)' }
    return $false
}

if (-not $Images -or $Images.Count -eq 0) {
    # .iso first: one is used as it is, the others need converting.
    $Images = @()
    $up = Split-Path -Parent $here
    foreach ($pat in '*.iso', '*.exe', '*.bin', '*.zip') {
        foreach ($dir in @($here, $up)) {
            if ($dir) { $Images += @(Get-ChildItem -LiteralPath $dir -Filter $pat -File | ForEach-Object { $_.FullName }) }
        }
    }
}
foreach ($img in $Images) {
    if (Test-Complete) { break }
    if (-not (Test-Path -LiteralPath $img -PathType Leaf)) { Fail "$img`: no such file" }
    $label = Split-Path -Leaf $img
    $lower = $img.ToLowerInvariant()
    if ($lower.EndsWith('.cue')) {
        $cue = [IO.File]::ReadAllText($img)
        $m = [regex]::Match($cue, '(?m)^\s*FILE\s+"([^"]+)"')
        if (-not $m.Success -or $cue -notmatch '(?i)TRACK\s+01\s+MODE[12]/2352') {
            Write-Host "  $label`: not a one-track MODE1/2352 or MODE2/2352 cue sheet; skipped"
            continue
        }
        $img = Join-Path (Split-Path -Parent $img) $m.Groups[1].Value
        if (-not (Test-Path -LiteralPath $img -PathType Leaf)) { Fail "$label names $($m.Groups[1].Value), which is not beside it" }
        $lower = '.bin'
    }
    if ($lower.EndsWith('.bin') -or $lower.EndsWith('.zip')) {
        $size = (Open-Raw $img -SizeOnly)[0]
        foreach ($id in @($imgs.Keys)) {
            $d = $imgs[$id]
            if ($d.Path -or $size -ne $d.Raw) { continue }
            $tmp = Join-Path $here ".disc-$($script:temps.Count).iso.part"
            $script:temps += $tmp
            Write-Host "converting $label to an .iso ..."
            Convert-Raw $img $tmp
            if (-not (Use-Image $tmp "$label (converted)")) { Remove-Item -LiteralPath $tmp -Force }
            break
        }
    } else {
        [void](Use-Image $img $label)
    }
}
if (-not (Test-Complete)) {
    Write-Host 'These are needed, and not all were found:' -ForegroundColor Red
    foreach ($s in $sets) {
        Write-Host "  $($s[0]):"
        foreach ($id in $s[1..($s.Count - 1)]) {
            $d = $imgs[$id]
            if ($d.Path) { Write-Host "    found:   $($d.Name)" }
            else { Write-Host "    missing: $($d.Name) ($($d.Size) bytes, SHA-256 $($d.Sha))" }
        }
    }
    Write-Host '  (a disc as an .iso, or redump''s .bin/.cue or .zip of it)'
    Fail 'drop both disc images and nolf2-update_1x3.exe on windows-install.bat, or put them in this folder'
}

# Raw deflate data, inflated: $pre (a stored block holding a dictionary,
# or $null) and then $count bytes of $buf from $off, into $dst from $at.
# Returns how many bytes it wrote.
function Expand-Deflate($pre, $buf, $off, $count, $dst, $at) {
    $ms = New-Object IO.MemoryStream
    if ($pre) { $ms.Write($pre, 0, $pre.Length) }
    $ms.Write($buf, $off, $count)
    $ms.Position = 0
    $z = New-Object IO.Compression.DeflateStream($ms, [IO.Compression.CompressionMode]::Decompress)
    $total = 0
    while ($true) {
        $n = $z.Read($dst, $at + $total, $dst.Length - $at - $total)
        if ($n -le 0) { break }
        $total += $n
    }
    $z.Close()
    return $total
}

# The update's payload (M <id> <of> <offset> <size> <sha>): the one folder of
# the Microsoft cabinet in it, unpacked. MSZIP blocks are "CK" and a deflate
# stream whose history is the previous block's last 32 KB: DeflateStream
# takes no dictionary, so each gets it as a stored block first, and that
# much of the output is dropped.
$memory = @{}
foreach ($l in $lines) {
    $p = $l.Split(' ')
    if ($p[0] -ne 'M' -or -not $imgs[$p[2]].Path) { continue }
    $exe = [IO.File]::ReadAllBytes($imgs[$p[2]].Path)
    $base = [int]$p[3]
    $size = [int]$p[4]
    $off = [BitConverter]::ToInt32($exe, $base + 36)
    $nblocks = [int][BitConverter]::ToUInt16($exe, $base + 40)
    $kind = [int][BitConverter]::ToUInt16($exe, $base + 42) -band 15
    $payload = New-Object byte[] ($size + 65536)
    $tmp = New-Object byte[] (32768 + 65536)
    $len = 0
    $pos = $base + $off
    for ($b = 0; $b -lt $nblocks; $b++) {
        $cb = [int][BitConverter]::ToUInt16($exe, $pos + 4)
        $cu = [int][BitConverter]::ToUInt16($exe, $pos + 6)
        if ($kind -eq 0) {
            [Array]::Copy($exe, $pos + 8, $payload, $len, $cb)
            $n = $cb
        } else {
            $w = [Math]::Min($len, 32768)
            $pre = $null
            if ($w -gt 0) {
                $pre = New-Object byte[] (5 + $w)
                $pre[1] = $w -band 255; $pre[2] = $w -shr 8
                $pre[3] = (-bnot $w) -band 255; $pre[4] = ((-bnot $w) -shr 8) -band 255
                [Array]::Copy($payload, $len - $w, $pre, 5, $w)
            }
            $n = (Expand-Deflate $pre $exe ($pos + 10) ($cb - 2) $tmp 0) - $w
            [Array]::Copy($tmp, $w, $payload, $len, $n)
        }
        if ($n -ne $cu) { Fail "$(Split-Path -Leaf $imgs[$p[2]].Path): its cabinet did not unpack right" }
        $len += $n
        $pos += 8 + $cb
    }
    $sha = [Security.Cryptography.SHA256]::Create()
    $sum = ([BitConverter]::ToString($sha.ComputeHash($payload, 0, $len)) -replace '-', '').ToLowerInvariant()
    if ($len -ne $size -or $sum -ne $p[5]) { Fail "$(Split-Path -Leaf $imgs[$p[2]].Path): its cabinet did not unpack right" }
    $memory[$p[1]] = New-Object IO.MemoryStream (, $payload)
}

# Each retail file (V <n> ...): the first way (W copy|is <id>:<offset>:<length>...)
# whose images are all here.
$ways = @{}
$vid = $null
foreach ($l in $lines) {
    $p = $l.Split(' ')
    if ($p[0] -eq 'V') { $vid = $p[1]; continue }
    if ($p[0] -ne 'W' -or $ways.ContainsKey($vid)) { continue }
    $ranges = @()
    $ok = $true
    foreach ($r in $p[2..($p.Count - 1)]) {
        $q = $r.Split(':')
        if (-not ($memory.ContainsKey($q[0]) -or ($imgs.ContainsKey($q[0]) -and $imgs[$q[0]].Path))) { $ok = $false }
        $ranges += , @($q[0], [int64]$q[1], [int64]$q[2])
    }
    if ($ok) { $ways[$vid] = @{ Kind = $p[1]; Ranges = $ranges } }
}

$streams = @{}
foreach ($id in $imgs.Keys) { if ($imgs[$id].Path) { $streams[$id] = [IO.File]::OpenRead($imgs[$id].Path) } }
foreach ($id in $memory.Keys) { $streams[$id] = $memory[$id] }

# A retail file being read, in order: its ranges, and (is) the chunk
# inflated last and how much of it is left.
function New-Reader($way) {
    return @{ Kind = $way.Kind; Ranges = $way.Ranges; Next = 0; Left = [int64]0; Src = $null
              Chunk = (New-Object byte[] 65536); At = 0; Have = 0 }
}
$raw = New-Object byte[] (65536)
# $count bytes of the ranges, joined, into $buf from $at.
function Read-Ranges($r, $buf, $at, $count) {
    while ($count -gt 0) {
        if ($r.Left -eq 0) {
            if ($r.Next -ge $r.Ranges.Count) { Fail 'a retail file ends early' }
            $q = $r.Ranges[$r.Next]
            $r.Next = $r.Next + 1
            $r.Src = $streams[$q[0]]
            $r.Src.Position = $q[1]
            $r.Left = $q[2]
        }
        $n = $r.Src.Read($buf, $at, [int][Math]::Min([int64]$count, [int64]$r.Left))
        if ($n -le 0) { Fail 'an image ended early' }
        $at += $n
        $count -= $n
        $r.Left -= $n
    }
}
# The next $count bytes of the retail file: to $dst (or dropped, $null).
function Read-File($r, $count, $dst) {
    while ($count -gt 0) {
        if ($r.Kind -eq 'copy') {
            $n = [int][Math]::Min([int64]$count, [int64]$raw.Length)
            Read-Ranges $r $raw 0 $n
            if ($dst) { $dst.Write($raw, 0, $n) }
            $count -= $n
            continue
        }
        if ($r.At -ge $r.Have) {
            Read-Ranges $r $raw 0 2
            $n = [int][BitConverter]::ToUInt16($raw, 0)
            Read-Ranges $r $raw 0 $n
            $r.Have = Expand-Deflate $null $raw 0 $n $r.Chunk 0
            $r.At = 0
        }
        $n = [int][Math]::Min([int64]$count, [int64]($r.Have - $r.At))
        if ($dst) { $dst.Write($r.Chunk, $r.At, $n) }
        $r.At += $n
        $count -= $n
    }
}

function Test-Done($path, $size, $sha) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
    if (([IO.FileInfo]$path).Length -ne $size) { return $false }
    return (Get-Sha256 $path) -eq $sha
}

$zero = New-Object byte[] (1MB)
$out = $null
$written = 0
$kept = 0
try {
    foreach ($l in $lines) {
        $p = $l.Split(' ')
        switch ($p[0]) {
            'F' {
                $name = $p[1]
                $dest = Join-Path $here ($name.Replace('/', [IO.Path]::DirectorySeparatorChar))
                $size = [int64]$p[2]
                $sha = $p[3]
                $part = "$dest.part"
                $skip = (($p[4] -eq 'once') -and (Test-Path -LiteralPath $dest)) -or (Test-Done $dest $size $sha)
                if ($skip) { $kept++ } else {
                    Write-Host $name
                    if (-not $ways.ContainsKey($p[5])) { Fail "$name`: none of the images found has it" }
                    $dir = Split-Path -Parent $dest
                    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
                    $out = [IO.File]::Create($part)
                    $src = New-Reader $ways[$p[5]]
                }
            }
            'C' {
                if ($skip) { continue }
                Read-File $src ([int64]$p[1]) $out
            }
            'Z' {
                if ($skip) { continue }
                Read-File $src ([int64]$p[1]) $null
                $left = [int64]$p[1]
                while ($left -gt 0) {
                    $n = [int][Math]::Min($left, [int64]$zero.Length)
                    $out.Write($zero, 0, $n)
                    $left -= $n
                }
            }
            'L' {
                if ($skip) { continue }
                $b = [Convert]::FromBase64String($p[1])
                Read-File $src $b.Length $null
                $out.Write($b, 0, $b.Length)
            }
            'E' {
                if ($skip) { continue }
                $out.Close()
                $out = $null
                if (-not (Test-Done $part $size $sha)) {
                    Remove-Item -LiteralPath $part -Force
                    Fail "$name came out wrong (a disk error?); the files before it are in place"
                }
                Move-Item -LiteralPath $part -Destination $dest -Force
                $written++
            }
        }
    }
} finally {
    if ($out) { $out.Close() }
    foreach ($s in $streams.Values) { $s.Close() }
    Remove-Temps                    # once nothing has them open
}
$save = Join-Path $here 'Save'
if (-not (Test-Path -LiteralPath $save)) { New-Item -ItemType Directory -Path $save | Out-Null }
Write-Host ''
Write-Host "done: $written files written, $kept already in place. Start the game with NOLF2.exe" -ForegroundColor Green
exit 0
