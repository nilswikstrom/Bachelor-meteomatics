# ============================================================
#  Script for å hente ut treffbilde fra XML-loggfiler
#  Legger range, cross og solutiontime til i samlet CSV-fil
# ============================================================

# --- KONFIGURASJON: fyll inn dine egne stier her ---
$loggMappe  = "PATH-TO-LOGFILE"  # Folder where XML-files are found
$outputFil  = "PATH-TO-OUTPUT-FILE\loghogger\treffbilde_logg.csv"  # Path to collected logfile (CSV)

# File names that needs to be read (in preferred order: target 1, 2, 3)
$xmlFiler = @(
    "TARGET-NO_Solution_fixed_and_status.xml",  # Target 1
    "TARGET-NO_Solution_fixed_and_status.xml",  # Target 2
    "TARGET-NO_Solution_fixed_and_status.xml"  # Target 3
)

# ------------------------------------------------------------

# Making sure that the output-folder exists
$outputMappe = Split-Path -Parent $outputFil
if (-not (Test-Path $outputMappe)) {
    New-Item -ItemType Directory -Path $outputMappe -Force | Out-Null
}


# If the output file does not exist already, create it and include column titles
if (-not (Test-Path $outputFil)) {
    "DTG;Maal;AA;Range;Cross" | Out-File -FilePath $outputFil -Encoding UTF8
}

# Helperfunction: Translating "202605082016023" to DTG-format "082016Z MAY 26"
function Format-Solutiontime {
    param([string]$raaTid)

    if ($raaTid.Length -ge 12) {
        $aar    = $raaTid.Substring(2, 2)   # two last numbers in the year
        $maaned = $raaTid.Substring(4, 2)   #
        $dag    = $raaTid.Substring(6, 2)
        $time   = $raaTid.Substring(8, 2)
        $min    = $raaTid.Substring(10, 2)

        # NATO month-abbreviations (english, capital letters)
        $manederNATO = @('JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')
        $maanedTekst = $manederNATO[[int]$maaned - 1]

        return "$dag$time$min`Z $maanedTekst $aar"
    }
    return $raaTid  # Returns rawdata if the format is unexpected
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
