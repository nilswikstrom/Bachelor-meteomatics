# mottaker_udp_batch.ps1 - Receive 375 consecutive UDP file transfers and log statistics.
#
# Usage:
#   .\mottaker_udp_batch.ps1 -Port 5001 -OutputDir C:\mottatt -LogFile C:\mottatt\receiver_log.csv `
#                            -ExpectedRuns 375 -Config baseline [-TimeoutSeconds 15]
#
# Packet format (matches sender_udp.py):
#   Data packet : [seq_nr 4B big-endian][total 4B big-endian][payload up to 1400B]
#   EOT packet  : [0xFFFFFFFF 4B big-endian][total 4B][SHA-256 hex 64B ASCII]
#
# Behavior:
#   - UDP socket is kept open for all iterations (not reopened per file)
#   - Each iteration receives packets until EOT is detected or timeout occurs
#   - File is reconstructed, SHA-256 verified, then deleted
#   - One CSV row is written per iteration
#   - Stops automatically after $ExpectedRuns iterations

param (
    [Parameter(Mandatory=$true)]
    [int]$Port,

    [Parameter(Mandatory=$true)]
    [string]$OutputDir,

    [Parameter(Mandatory=$true)]
    [string]$LogFile,

    [Parameter(Mandatory=$true)]
    [int]$ExpectedRuns,

    [Parameter(Mandatory=$true)]
    [string]$Config,

    # Seconds without any packet before the current transfer is considered timed out
    [int]$TimeoutSeconds = 15
)

$EOT_MAGIC = [uint32]::MaxValue

# Helper: parse a big-endian uint32 from a byte array at the given offset
function Read-BigEndianUInt32 {
    param ([byte[]]$Bytes, [int]$Offset = 0)
    return ([uint32]$Bytes[$Offset]   -shl 24) -bor `
           ([uint32]$Bytes[$Offset+1] -shl 16) -bor `
           ([uint32]$Bytes[$Offset+2] -shl  8) -bor `
           ([uint32]$Bytes[$Offset+3])
}

# Helper: compute SHA-256 hex string from a byte array
function Get-SHA256Hex {
    param ([byte[]]$Data)
    $sha256    = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $sha256.ComputeHash($Data)
    $sha256.Dispose()
    return ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# Ensure output directory exists
if (-not (Test-Path $OutputDir)) {
    try {
        New-Item -ItemType Directory -Path $OutputDir -ErrorAction Stop | Out-Null
        Write-Host "[INFO] Created output directory: $OutputDir"
    } catch {
        Write-Host "[ERROR] Could not create output directory '$OutputDir': $_"
        exit 1
    }
}

# Write CSV header only if the log file does not already exist
if (-not (Test-Path $LogFile)) {
    "seq_nr,timestamp,config,sha256_received,packets_received,missing_packets,integrity_result" |
        Out-File -FilePath $LogFile -Encoding utf8 -NoNewline
    Add-Content -Path $LogFile -Value ""
    Write-Host "[INFO] Created log file: $LogFile"
} else {
    Write-Host "[INFO] Appending to existing log file: $LogFile"
}

# Open a single UDP socket that remains open for all iterations
Write-Host "[INFO] Opening UDP socket on port $Port ..."
$udp = [System.Net.Sockets.UdpClient]::new($Port)
$udp.Client.ReceiveBufferSize = 4 * 1024 * 1024
$udp.Client.ReceiveTimeout    = $TimeoutSeconds * 1000

$remoteEP = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, 0)

Write-Host "[INFO] Waiting for $ExpectedRuns transfers (timeout: $TimeoutSeconds s each) ..."
Write-Host ""

for ($runIndex = 0; $runIndex -lt $ExpectedRuns; $runIndex++) {

    $packets        = @{}
    $totalPackets   = $null
    $senderChecksum = $null
    $eotReceived    = $false
    $timedOut       = $false

    while (-not $eotReceived) {
        try {
            $data = $udp.Receive([ref]$remoteEP)
        } catch [System.Net.Sockets.SocketException] {
            $timedOut = $true
            break
        }

        if ($data.Length -lt 8) { continue }

        $seqNr = Read-BigEndianUInt32 -Bytes $data -Offset 0
        $total = Read-BigEndianUInt32 -Bytes $data -Offset 4

        if ($seqNr -eq $EOT_MAGIC) {
            if ($data.Length -ge 72) {
                $senderChecksum = [System.Text.Encoding]::ASCII.GetString($data, 8, 64)
            }
            $totalPackets = $total
            $eotReceived  = $true

            # Drain any duplicate EOT packets still in the buffer (sender sends EOT 5x).
            # Use a 150ms window - long enough to catch all duplicates, short enough to
            # not delay the next transfer noticeably.
            $udp.Client.ReceiveTimeout = 150
            try { while ($true) { $udp.Receive([ref]$remoteEP) | Out-Null } } catch { }
            $udp.Client.ReceiveTimeout = $TimeoutSeconds * 1000

        } else {
            if (-not $packets.ContainsKey($seqNr)) {
                $payload = New-Object byte[] ($data.Length - 8)
                [System.Array]::Copy($data, 8, $payload, 0, $payload.Length)
                $packets[$seqNr] = $payload
            }
            if ($null -eq $totalPackets) { $totalPackets = $total }
        }
    }

    $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")

    if ($timedOut -and -not $eotReceived) {
        $packetsReceived = $packets.Count
        $missingPackets  = if ($null -ne $totalPackets) { $totalPackets - $packetsReceived } else { 0 }
        $csvLine = "$runIndex,$timestamp,$Config,,$packetsReceived,$missingPackets,TIMEOUT"
        Add-Content -Path $LogFile -Value $csvLine
        Write-Host "[$($runIndex + 1)/$ExpectedRuns] TIMEOUT | packets received: $packetsReceived"
        continue
    }

    $packetsReceived = $packets.Count
    $missingPackets  = $totalPackets - $packetsReceived

    $ms = [System.IO.MemoryStream]::new()
    for ($i = 0; $i -lt [int]$totalPackets; $i++) {
        $key = [uint32]$i
        if ($packets.ContainsKey($key)) {
            $ms.Write($packets[$key], 0, $packets[$key].Length)
        }
    }
    $fileBytes = $ms.ToArray()
    $ms.Dispose()

    $sha256Received = Get-SHA256Hex -Data $fileBytes

    if ($null -ne $senderChecksum -and $sha256Received -eq $senderChecksum) {
        $result = "PASS"
    } else {
        $result = "FAIL"
    }

    $csvLine = "$runIndex,$timestamp,$Config,$sha256Received,$packetsReceived,$missingPackets,$result"
    Add-Content -Path $LogFile -Value $csvLine

    Write-Host "[$($runIndex + 1)/$ExpectedRuns] $result | packets: $packetsReceived/$totalPackets | missing: $missingPackets"
}

$udp.Close()
Write-Host ""
Write-Host "[INFO] Batch complete - $ExpectedRuns iterations processed."
Write-Host "[INFO] Results written to: $LogFile"
