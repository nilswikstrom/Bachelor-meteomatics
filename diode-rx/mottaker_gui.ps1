#Requires -Version 5.0
# mottaker_gui.ps1 - GUI wrapper around mottaker_udp.ps1.
# Launches the receiver script, streams its output to the log window,
# and shows where the file ended up when the transfer is complete.
#
# Both mottaker_gui.ps1 and mottaker_udp.ps1 must be in the same folder.
# Run via start_mottaker.bat (no terminal window).

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# -- Helpers --
function C($hex) { [System.Drawing.ColorTranslator]::FromHtml($hex) }
function Pt($x, $y) { [System.Drawing.Point]::new($x, $y) }
function Sz($w, $h) { [System.Drawing.Size]::new($w, $h) }

$BG    = C "#0d1117"
$PNL   = C "#161b22"
$ENT   = C "#21262d"
$GRN   = C "#3fb950"
$AMB   = C "#d29922"
$RED   = C "#f85149"
$WHT   = C "#e6edf3"
$DIM   = C "#8b949e"
$ACC   = C "#1f6feb"
$BRD   = C "#30363d"
$SVDBG = C "#0d2010"

$FMONO  = New-Object System.Drawing.Font("Courier New", 9)
$FTITLE = New-Object System.Drawing.Font("Courier New", 12, [System.Drawing.FontStyle]::Bold)
$FBTN   = New-Object System.Drawing.Font("Courier New", 9,  [System.Drawing.FontStyle]::Bold)
$FSMALL = New-Object System.Drawing.Font("Courier New", 8)

$shared = [hashtable]::Synchronized(@{
    Cancel   = $false
    Messages = [System.Collections.Concurrent.ConcurrentQueue[string]]::new()
    PS       = $null
    Runspace = $null
})

# -- Worker: launches mottaker_udp.ps1 and forwards its output --
$workerScript = {
    param([string]$ScriptPath, [int]$Port, [string]$OutputPath, [int]$TimeoutSeconds, [hashtable]$Shared)

    function Q($msg) { $Shared.Messages.Enqueue($msg) }

    if (-not (Test-Path $ScriptPath)) {
        Q "LOG:ERROR:[FEIL] Finner ikke mottaker_udp.ps1 i samme mappe som GUI-en"
        Q "DONE_FAIL:"
        return
    }

    # Encode the command as base64 UTF-16 so special characters in paths (e.g. ø in
    # folder names like "dataoverføring") survive the Windows command-line parser.
    # *>&1 merges all PS streams (incl. Write-Host / Information stream 6) into stdout
    $cmd     = "& '$($ScriptPath -replace "'","''")' -Port $Port -OutputPath '$($OutputPath -replace "'","''")' -TimeoutSeconds $TimeoutSeconds *>&1"
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($cmd))

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = "powershell.exe"
    $psi.Arguments              = "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded"
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi

    try {
        $proc.Start() | Out-Null
    } catch {
        Q "LOG:ERROR:[FEIL] Kunne ikke starte prosess: $_"
        Q "DONE_FAIL:"
        return
    }

    # Read stdout line by line until the process exits
    $reader = $proc.StandardOutput
    while (-not $reader.EndOfStream) {
        if ($Shared.Cancel) { $proc.Kill(); break }
        $line = $reader.ReadLine()
        if ($null -ne $line) {
            $line = $line.TrimEnd("`r").Trim()
            if ($line -ne "") { Q "LINE:$line" }
        }
    }

    $proc.WaitForExit()

    # Capture stderr - skip CLIXML progress blobs (harmless PS internal metadata)
    $errOut = $proc.StandardError.ReadToEnd().Trim()
    if ($errOut -ne "" -and -not $errOut.StartsWith("#< CLIXML")) {
        foreach ($eLine in ($errOut -split "`n")) {
            $eLine = $eLine.TrimEnd("`r").Trim()
            if ($eLine -ne "") { Q "LINE:[STDERR] $eLine" }
        }
    }

    if ($Shared.Cancel) {
        Q "LOG:WARN:[INFO] Avbrutt av bruker"
        Q "DONE_FAIL:"
    } elseif ($proc.ExitCode -eq 0) {
        Q "DONE_OK:$OutputPath"
    } else {
        Q "LOG:ERROR:[FEIL] mottaker_udp.ps1 avsluttet med feil (kode $($proc.ExitCode))"
        Q "DONE_FAIL:"
    }
}

# -- Form --
$form = New-Object System.Windows.Forms.Form
$form.Text            = "METCM / METGM MOTTAKER - <<name-of-IT-system>>"
$form.BackColor       = $BG
$form.ForeColor       = $WHT
$form.Font            = $FMONO
$form.ClientSize      = Sz 640 540
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox     = $false
$form.StartPosition   = [System.Windows.Forms.FormStartPosition]::CenterScreen

# Header
$pnlHeader = New-Object System.Windows.Forms.Panel
$pnlHeader.Location  = Pt 0 0
$pnlHeader.Size      = Sz 640 66
$pnlHeader.BackColor = $PNL
$form.Controls.Add($pnlHeader)

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text      = "METCM / METGM MOTTAKER"
$lblTitle.Font      = $FTITLE
$lblTitle.ForeColor = $GRN
$lblTitle.BackColor = [System.Drawing.Color]::Transparent
$lblTitle.Location  = Pt 18 10
$lblTitle.AutoSize  = $true
$pnlHeader.Controls.Add($lblTitle)

$lblSub = New-Object System.Windows.Forms.Label
$lblSub.Text      = "<<name-of-IT-system>>  .  Enveis UDP-mottaker  .  STANAG 4082 / 6022"
$lblSub.Font      = $FSMALL
$lblSub.ForeColor = $DIM
$lblSub.BackColor = [System.Drawing.Color]::Transparent
$lblSub.Location  = Pt 18 38
$lblSub.AutoSize  = $true
$pnlHeader.Controls.Add($lblSub)

$pnlAccent = New-Object System.Windows.Forms.Panel
$pnlAccent.Location  = Pt 0 66
$pnlAccent.Size      = Sz 640 3
$pnlAccent.BackColor = $ACC
$form.Controls.Add($pnlAccent)

# Config
function Add-Lbl($text, $x, $y) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text; $l.ForeColor = $DIM
    $l.BackColor = [System.Drawing.Color]::Transparent
    $l.Location = Pt $x $y; $l.AutoSize = $true
    $form.Controls.Add($l)
}
function Add-Txt($x, $y, $w, $val) {
    $t = New-Object System.Windows.Forms.TextBox
    $t.Text = $val; $t.BackColor = $ENT; $t.ForeColor = $WHT
    $t.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
    $t.Location = Pt $x $y; $t.Size = Sz $w 22
    $form.Controls.Add($t); return $t
}

Add-Lbl "UDP-PORT"   18 86
$txtPort    = Add-Txt 115 84 70 "5001"

Add-Lbl "TIMEOUT (s)" 200 86
$txtTimeout = Add-Txt 310 84 50 "10"

Add-Lbl "LAGRE TIL" 18 116
$txtPath = Add-Txt 115 114 450 "C:\mottatt\metcm_mottatt.bin"

$btnBrowse = New-Object System.Windows.Forms.Button
$btnBrowse.Text = "..."; $btnBrowse.BackColor = $ENT; $btnBrowse.ForeColor = $WHT
$btnBrowse.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnBrowse.FlatAppearance.BorderColor = $BRD
$btnBrowse.Location = Pt 572 113; $btnBrowse.Size = Sz 46 24
$btnBrowse.Cursor = [System.Windows.Forms.Cursors]::Hand
$form.Controls.Add($btnBrowse)

# Separator
$s1 = New-Object System.Windows.Forms.Panel
$s1.Location = Pt 0 148; $s1.Size = Sz 640 1; $s1.BackColor = $BRD
$form.Controls.Add($s1)

# Status bar
$pnlStat = New-Object System.Windows.Forms.Panel
$pnlStat.Location = Pt 0 149; $pnlStat.Size = Sz 640 38; $pnlStat.BackColor = $PNL
$form.Controls.Add($pnlStat)

$lblStatKey = New-Object System.Windows.Forms.Label
$lblStatKey.Text = "STATUS :"; $lblStatKey.ForeColor = $DIM
$lblStatKey.BackColor = [System.Drawing.Color]::Transparent
$lblStatKey.Location = Pt 18 10; $lblStatKey.AutoSize = $true
$pnlStat.Controls.Add($lblStatKey)

$lblStatVal = New-Object System.Windows.Forms.Label
$lblStatVal.Text = "VENTER"; $lblStatVal.Font = $FBTN
$lblStatVal.ForeColor = $DIM; $lblStatVal.BackColor = [System.Drawing.Color]::Transparent
$lblStatVal.Location = Pt 100 10; $lblStatVal.Size = Sz 200 20
$pnlStat.Controls.Add($lblStatVal)

# Progress bar (Marquee while receiving)
$pbRecv = New-Object System.Windows.Forms.ProgressBar
$pbRecv.Location = Pt 18 198; $pbRecv.Size = Sz 602 20
$pbRecv.Style = [System.Windows.Forms.ProgressBarStyle]::Continuous
$pbRecv.Minimum = 0; $pbRecv.Maximum = 100; $pbRecv.Value = 0
$form.Controls.Add($pbRecv)

$lblPkt = New-Object System.Windows.Forms.Label
$lblPkt.Text = ""; $lblPkt.Font = $FSMALL; $lblPkt.ForeColor = $DIM
$lblPkt.BackColor = [System.Drawing.Color]::Transparent
$lblPkt.Location = Pt 18 221; $lblPkt.Size = Sz 602 16
$lblPkt.TextAlign = [System.Drawing.ContentAlignment]::MiddleRight
$form.Controls.Add($lblPkt)

# Log
$txtLog = New-Object System.Windows.Forms.RichTextBox
$txtLog.Location = Pt 18 242; $txtLog.Size = Sz 602 198
$txtLog.BackColor = $PNL; $txtLog.ForeColor = $DIM; $txtLog.Font = $FSMALL
$txtLog.ReadOnly = $true
$txtLog.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$txtLog.ScrollBars = [System.Windows.Forms.RichTextBoxScrollBars]::Vertical
$form.Controls.Add($txtLog)

$s2 = New-Object System.Windows.Forms.Panel
$s2.Location = Pt 0 450; $s2.Size = Sz 640 1; $s2.BackColor = $BRD
$form.Controls.Add($s2)

# Buttons
$pnlBtns = New-Object System.Windows.Forms.Panel
$pnlBtns.Location = Pt 0 451; $pnlBtns.Size = Sz 640 62; $pnlBtns.BackColor = $PNL
$form.Controls.Add($pnlBtns)

$btnStart = New-Object System.Windows.Forms.Button
$btnStart.Text = "KLAR TIL A MOTTA"; $btnStart.Font = $FBTN
$btnStart.BackColor = $GRN; $btnStart.ForeColor = $BG
$btnStart.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnStart.FlatAppearance.BorderSize = 0
$btnStart.Location = Pt 18 13; $btnStart.Size = Sz 180 36
$btnStart.Cursor = [System.Windows.Forms.Cursors]::Hand
$pnlBtns.Controls.Add($btnStart)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "AVBRYT"; $btnCancel.Font = $FBTN
$btnCancel.BackColor = $ENT; $btnCancel.ForeColor = $DIM
$btnCancel.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnCancel.FlatAppearance.BorderColor = $BRD
$btnCancel.Location = Pt 212 13; $btnCancel.Size = Sz 100 36
$btnCancel.Cursor = [System.Windows.Forms.Cursors]::Hand; $btnCancel.Enabled = $false
$pnlBtns.Controls.Add($btnCancel)

# Saved-path bar
$pnlSaved = New-Object System.Windows.Forms.Panel
$pnlSaved.Location = Pt 0 513; $pnlSaved.Size = Sz 640 28
$pnlSaved.BackColor = $SVDBG; $pnlSaved.Visible = $false
$form.Controls.Add($pnlSaved)

$lblSavedKey = New-Object System.Windows.Forms.Label
$lblSavedKey.Text = "FIL LAGRET TIL :"; $lblSavedKey.Font = $FSMALL
$lblSavedKey.ForeColor = $DIM; $lblSavedKey.BackColor = [System.Drawing.Color]::Transparent
$lblSavedKey.Location = Pt 18 7; $lblSavedKey.AutoSize = $true
$pnlSaved.Controls.Add($lblSavedKey)

$lblSavedPath = New-Object System.Windows.Forms.Label
$lblSavedPath.Text = ""; $lblSavedPath.Font = $FMONO
$lblSavedPath.ForeColor = $GRN; $lblSavedPath.BackColor = [System.Drawing.Color]::Transparent
$lblSavedPath.Location = Pt 145 7; $lblSavedPath.Size = Sz 475 18
$pnlSaved.Controls.Add($lblSavedPath)

# -- Log helper --
function Write-Log($text, $color) {
    $ts = (Get-Date).ToString("HH:mm:ss")
    $txtLog.SelectionStart = $txtLog.TextLength; $txtLog.SelectionLength = 0
    $txtLog.SelectionColor = $DIM; $txtLog.AppendText("[${ts}]  ")
    $txtLog.SelectionColor = $color; $txtLog.AppendText("${text}`n")
    $txtLog.ScrollToCaret()
}
function Reset-Buttons {
    $btnStart.Enabled = $true
    $btnCancel.Enabled = $false; $btnCancel.BackColor = $ENT; $btnCancel.ForeColor = $DIM
}

# -- Timer --
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 80

$timer.Add_Tick({
    $msg = $null
    while ($shared.Messages.TryDequeue([ref]$msg)) {

        if ($msg.StartsWith("LINE:")) {
            $line = $msg.Substring(5)
            $col = $DIM
            if ($line.StartsWith("[OK]"))    { $col = $GRN }
            elseif ($line.StartsWith("[WARN]"))  { $col = $AMB }
            elseif ($line.StartsWith("[ERROR]")) { $col = $RED }
            Write-Log $line $col
            # Show packet count as it trickles in
            if ($line -match "Received (\d+) unique") {
                $lblPkt.Text = "Mottatt: $($Matches[1]) pakker..."
            }
            elseif ($line -match "EOT received.*total expected: (\d+)") {
                $lblPkt.Text = "EOT - totalt $($Matches[1]) pakker"
            }

        } elseif ($msg.StartsWith("LOG:")) {
            $parts = $msg.Split(":", 3)
            $col = switch ($parts[1]) {
                "OK"    { $GRN } "WARN" { $AMB } "ERROR" { $RED } default { $DIM }
            }
            Write-Log $parts[2] $col

        } elseif ($msg.StartsWith("DONE_OK:")) {
            $outPath = $msg.Substring(8)
            $lblStatVal.Text = "FERDIG"; $lblStatVal.ForeColor = $GRN
            $pbRecv.Style = [System.Windows.Forms.ProgressBarStyle]::Continuous
            $pbRecv.Value = 100; $lblPkt.Text = "Overfoering fullfort"
            $lblSavedPath.Text = $outPath; $pnlSaved.Visible = $true
            Reset-Buttons; $timer.Stop()

        } elseif ($msg -eq "DONE_FAIL:") {
            $lblStatVal.Text = "FEIL"; $lblStatVal.ForeColor = $RED
            $pbRecv.Style = [System.Windows.Forms.ProgressBarStyle]::Continuous
            $pbRecv.Value = 0; $lblPkt.Text = ""
            Reset-Buttons; $timer.Stop()
        }
    }
})

# -- Button handlers --
$btnBrowse.Add_Click({
    $dlg = New-Object System.Windows.Forms.SaveFileDialog
    $dlg.Filter = "Binaerfiler (*.bin)|*.bin|Alle filer (*.*)|*.*"
    $dlg.Title = "Velg lagringsplass"; $dlg.DefaultExt = "bin"
    if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $txtPath.Text = $dlg.FileName
    }
})

$btnStart.Add_Click({
    $port = 0
    if (-not [int]::TryParse($txtPort.Text.Trim(), [ref]$port) -or $port -lt 1 -or $port -gt 65535) {
        Write-Log "[FEIL] Ugyldig portnummer" $RED; return
    }
    $timeout = 0
    if (-not [int]::TryParse($txtTimeout.Text.Trim(), [ref]$timeout) -or $timeout -lt 1) {
        Write-Log "[FEIL] Ugyldig timeout - must vaere et positivt heltall" $RED; return
    }
    $outPath = $txtPath.Text.Trim()
    if (-not $outPath) { Write-Log "[FEIL] Velg lagringsplass" $RED; return }

    # mottaker_udp.ps1 must be next to mottaker_gui.ps1
    $scriptDir = $PSScriptRoot
    $udpScript = Join-Path $scriptDir "mottaker_udp.ps1"
    Write-Log "[INFO] Script: $udpScript" $DIM

    $pnlSaved.Visible = $false
    $shared.Cancel = $false
    $btnStart.Enabled = $false
    $btnCancel.Enabled = $true; $btnCancel.BackColor = C "#3d1c1c"; $btnCancel.ForeColor = $RED
    $lblStatVal.Text = "LYTTER..."; $lblStatVal.ForeColor = $AMB
    $pbRecv.Style = [System.Windows.Forms.ProgressBarStyle]::Marquee
    $pbRecv.MarqueeAnimationSpeed = 30; $pbRecv.Value = 0; $lblPkt.Text = ""

    Write-Log "[INFO] Starter mottaker_udp.ps1 paa port $port..." $DIM
    Write-Log "[INFO] Lagrer til : $outPath" $DIM

    $rs = [System.Management.Automation.Runspaces.RunspaceFactory]::CreateRunspace()
    $rs.Open()
    $ps = [System.Management.Automation.PowerShell]::Create()
    $ps.Runspace = $rs
    $ps.AddScript($workerScript).AddArgument($udpScript).AddArgument($port).AddArgument($outPath).AddArgument($timeout).AddArgument($shared) | Out-Null
    $shared.PS = $ps; $shared.Runspace = $rs
    $ps.BeginInvoke() | Out-Null
    $timer.Start()
})

$btnCancel.Add_Click({
    $shared.Cancel = $true
    Write-Log "[INFO] Avbryter..." $AMB
})

$form.Add_FormClosed({
    $shared.Cancel = $true; $timer.Stop()
    if ($null -ne $shared.PS)       { try { $shared.PS.Stop()        } catch {} }
    if ($null -ne $shared.Runspace) { try { $shared.Runspace.Close() } catch {} }
})

[System.Windows.Forms.Application]::Run($form)
