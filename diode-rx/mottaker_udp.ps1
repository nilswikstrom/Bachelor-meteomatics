# mottaker_udp.ps1 - Receive a file via UDP, reconstruct, and verify SHA-256.
#
# Usage:
#   .\mottaker_udp.ps1 -Port 5001 -OutputPath C:\mottatt\metcm.bin
#
# Packet format (matches sender_udp.py):
#   Data packet : [seq_nr 4B big-endian][total 4B big-endian][payload]
#   EOT packet  : [0xFFFFFFFF 4B][total 4B][checksum 32B ASCII hex]
#
# Behavior:
#   - Receives packets until EOT is detected
#   - Duplicate packets (from redundancy) are silently ignored
#   - Missing packets are logged after EOT
#   - File is reconstructed from received packets in order
#   - SHA-256 of reconstructed file is compared to sender's checksum

param (
    [Parameter(Mandatory=$true)]
    [int]$Port,

    [Parameter(Mandatory=$true)]
    [string]$OutputPath,

    # Seconds of silence after last packet before timing out (failsafe)
    [int]$TimeoutSeconds = 10
)

$EOT_MAGIC = [uint32]::MaxValue

# Ensure output directory exists
$outputDir = Split-Path -Parent $OutputPath
if ($outputDir -and -not (Test-Path $outputDir)) {
    try {
        New-Item -ItemType Directory -Path $outputDir -ErrorAction Stop | Out-Null
        Write-Host "[INFO] Created directory: $outputDir"
    } catch {
        Write-Host "[ERROR] Could not create output directory '$outputDir': $_"
        Write-Host "[ERROR] Create it manually: New-Item -ItemType Directory -Path '$outputDir'"
        exit 1
    }
}

# Helper: read big-endian uint32 from 4 bytes
function Read-BigEndianUInt32 {
    param ([byte[]]$Bytes, [int]$Offset = 0)
    return ([uint32]$Bytes[$Offset]   -shl 24) -bor `
           ([uint32]$Bytes[$Offset+1] -shl 16) -bor `
           ([uint32]$Bytes[$Offset+2] -shl  8) -bor `
           ([uint32]$Bytes[$Offset+3])
}

Write-Host "[INFO] Listening on UDP port $Port ..."
Write-Host "[INFO] Output file : $OutputPath"
Write-Host "[INFO] Timeout     : $TimeoutSeconds seconds after last packet"

$udp = [System.Net.Sockets.UdpClient]::new($Port)

# Increase receive buffer to 4 MB to reduce OS-level packet drops during bursts
$udp.Client.ReceiveBufferSize = 4 * 1024 * 1024

# Set receive timeout so we don't block forever waiting for EOT
$udp.Client.ReceiveTimeout = $TimeoutSeconds * 1000

$remoteEP     = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, 0)
$packets      = @{}   # hashtable: seq_nr -> payload (byte[])
$totalPackets = $null
$senderChecksum = $null
$eotReceived  = $false

try {
    while (-not $eotReceived) {
        try {
            $data = $udp.Receive([ref]$remoteEP)
        } catch {
            $inner = $_.Exception.InnerException -as [System.Net.Sockets.SocketException]
            if ($inner -and $inner.SocketErrorCode -eq [System.Net.Sockets.SocketError]::TimedOut) {
                Write-Host ""
                Write-Host "[WARN] Receive timed out after $TimeoutSeconds seconds - proceeding with what was received"
                break
            }
            throw
        }

        if ($data.Length -lt 8) {
            Write-Host "[WARN] Packet too short ($($data.Length) bytes) - skipping"
            continue
        }

        $seqNr = Read-BigEndianUInt32 -Bytes $data -Offset 0
        $total = Read-BigEndianUInt32 -Bytes $data -Offset 4

        if ($seqNr -eq $EOT_MAGIC) {
            # This is the end-of-transfer packet
            if ($data.Length -ge 72) {
                $senderChecksum = [System.Text.Encoding]::ASCII.GetString($data, 8, 64)
            }
            $totalPackets = $total
            $eotReceived  = $true
            Write-Host ""
            Write-Host "[INFO] EOT received - total expected: $total packets"

        } else {
            # Normal data packet - store payload (ignore duplicates)
            if (-not $packets.ContainsKey($seqNr)) {
                $payload = New-Object byte[] ($data.Length - 8)
                [System.Array]::Copy($data, 8, $payload, 0, $payload.Length)
                $packets[$seqNr] = $payload
            }

            # Progress - only print every 10 new packets to reduce console spam
            if ($packets.Count % 10 -eq 0) {
                Write-Host "[INFO] Received $($packets.Count) unique packets so far..." -NoNewline
                Write-Host "`r" -NoNewline
            }

            # Update total if not yet set (arrives from any data packet)
            if ($null -eq $totalPackets) {
                $totalPackets = $total
            }
        }
    }
} finally {
    $udp.Close()
}

Write-Host "[INFO] Unique packets received : $($packets.Count)"

if ($null -eq $totalPackets) {
    Write-Host "[ERROR] No packets received - nothing to reconstruct"
    exit 1
}

# Report missing packets
$missing = @()
for ($i = 0; $i -lt $totalPackets; $i++) {
    if (-not $packets.ContainsKey([uint32]$i)) {
        $missing += $i
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[WARN] Missing $($missing.Count) of $totalPackets packets:"
    # Print at most 20 missing sequence numbers to keep output readable
    $showCount = [Math]::Min($missing.Count, 20)
    Write-Host "[WARN] Missing seq numbers (first $showCount): $($missing[0..($showCount-1)] -join ', ')"
    if ($missing.Count -gt 20) {
        Write-Host "[WARN] ... and $($missing.Count - 20) more"
    }
} else {
    Write-Host "[OK] All $totalPackets packets received"
}

# Reconstruct file by writing packets in order
Write-Host "[INFO] Reconstructing file ..."
$fileStream = [System.IO.File]::OpenWrite($OutputPath)
try {
    for ($i = 0; $i -lt $totalPackets; $i++) {
        $key = [uint32]$i
        if ($packets.ContainsKey($key)) {
            $fileStream.Write($packets[$key], 0, $packets[$key].Length)
        } else {
            # Fill missing chunk with zero bytes - length unknown without
            # a complete packet, so we cannot reconstruct exactly.
            # The checksum will catch this and report failure.
            Write-Host "[WARN] Packet $i missing - gap in reconstructed file"
        }
    }
} finally {
    $fileStream.Close()
}

Write-Host "[INFO] File written to $OutputPath"

# Compute SHA-256 of reconstructed file
$sha256           = [System.Security.Cryptography.SHA256]::Create()
$fileBytes        = [System.IO.File]::ReadAllBytes($OutputPath)
$hashBytes        = $sha256.ComputeHash($fileBytes)
$receiverChecksum = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""

Write-Host "[INFO] Sender   SHA-256: $senderChecksum"
Write-Host "[INFO] Receiver SHA-256: $receiverChecksum"

if ($null -eq $senderChecksum) {
    Write-Host "[WARN] No EOT packet received - cannot verify checksum"
} elseif ($senderChecksum -eq $receiverChecksum) {
    Write-Host "[OK] Integrity check PASSED"
} else {
    Write-Host "[ERROR] Integrity check FAILED"
    if ($missing.Count -gt 0) {
        Write-Host "[ERROR] Likely cause: $($missing.Count) missing packet(s)"
        Write-Host "[ERROR] Consider increasing -repeats on the sender"
    }
    exit 1
}
