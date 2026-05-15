# ============================================================
#  Script for å hente ut treffbilde fra XML-loggfiler
#  Legger range, cross og solutiontime til i samlet CSV-fil
# ============================================================

# --- KONFIGURASJON: fyll inn dine egne stier her ---
$loggMappe  = "C:\ProgramData\KDA\ODIN_FSS\logs\Fire Support XML Log"                          # Mappe der XML-filene ligger
$outputFil  = "E:\Bachelor\ODIN-loghogger\treffbilde_logg.csv"         # Samlet loggfil (CSV)

# Filnavn som skal leses (i ønsket rekkefølge: mål 1, 2, 3)
$xmlFiler = @(
    "AA0001_Solution_fixed_and_status.xml",
    "AA0002_Solution_fixed_and_status.xml",
    "AA0003_Solution_fixed_and_status.xml"
)

# ------------------------------------------------------------

# Sørg for at output-mappen finnes
$outputMappe = Split-Path -Parent $outputFil
if (-not (Test-Path $outputMappe)) {
    New-Item -ItemType Directory -Path $outputMappe -Force | Out-Null
}

# Hvis output-filen ikke finnes fra før, lag den med kolonneoverskrifter
if (-not (Test-Path $outputFil)) {
    "DTG;Maal;AA;Range;Cross" | Out-File -FilePath $outputFil -Encoding UTF8
}

# Hjelpefunksjon: gjør om "202605082016023" til DTG-format "082016Z MAY 26"
function Format-Solutiontime {
    param([string]$raaTid)

    if ($raaTid.Length -ge 12) {
        $aar    = $raaTid.Substring(2, 2)   # to siste sifre i året
        $maaned = $raaTid.Substring(4, 2)
        $dag    = $raaTid.Substring(6, 2)
        $time   = $raaTid.Substring(8, 2)
        $min    = $raaTid.Substring(10, 2)

        # NATO månedsforkortelser (engelsk, store bokstaver)
        $manederNATO = @('JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')
        $maanedTekst = $manederNATO[[int]$maaned - 1]

        return "$dag$time$min`Z $maanedTekst $aar"
    }
    return $raaTid  # returner rådata hvis formatet er uventet
}

Write-Host "Henter ut treffbilde fra $($xmlFiler.Count) filer..." -ForegroundColor Cyan

$maalNr = 1
foreach ($filnavn in $xmlFiler) {
    $filsti = Join-Path $loggMappe $filnavn

    # Trekk ut AA-identifikatoren fra filnavnet (f.eks. "AA0001" fra hele filnavnet)
    $aaId = if ($filnavn -match '^(AA\d{4})') { $Matches[1] } else { $filnavn }

    if (-not (Test-Path $filsti)) {
        Write-Warning "Finner ikke filen: $filsti"
        $maalNr++
        continue
    }

    try {
        [xml]$xml = Get-Content -Path $filsti -Raw

        # Hent ut verdier (SelectSingleNode finner taggene uansett hvor de er i XML-en)
        $rangeNode = $xml.SelectSingleNode("//missdistance/range")
        $crossNode = $xml.SelectSingleNode("//missdistance/cross")
        $tidNode   = $xml.SelectSingleNode("//solutiontime")

        if ($null -eq $rangeNode -or $null -eq $crossNode) {
            Write-Warning "Mangler <missdistance> data i $filnavn"
            $maalNr++
            continue
        }

        $range        = $rangeNode.InnerText.Trim()
        $cross        = $crossNode.InnerText.Trim()
        $solutiontime = if ($tidNode) { Format-Solutiontime $tidNode.InnerText.Trim() } else { "" }

        # Skriv én linje til CSV-filen
        $linje = "$solutiontime;$maalNr;$aaId;$range;$cross"
        Add-Content -Path $outputFil -Value $linje -Encoding UTF8

        Write-Host ("  Maal {0} ({1}): range = {2,-12} cross = {3,-12} ({4})" -f `
                    $maalNr, $aaId, $range, $cross, $solutiontime) -ForegroundColor Green
    }
    catch {
        Write-Warning "Feil ved lesing av $filnavn : $_"
    }

    $maalNr++
}

Write-Host "`nFerdig! Data lagt til i:" -ForegroundColor Cyan
Write-Host "  $outputFil"