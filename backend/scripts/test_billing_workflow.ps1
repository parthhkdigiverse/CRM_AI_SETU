Set-Location "e:/CRM AI SETU"
$base = "http://127.0.0.1:8000/api"

function Step([string]$msg) { Write-Output ("`n=== " + $msg + " ===") }

Step "Login"
$loginBody = "username=admin@example.com&password=password123"
$login = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -ContentType "application/x-www-form-urlencoded" -Body $loginBody
$token = $login.access_token
if (-not $token) { throw "No token returned" }
$headers = @{ Authorization = "Bearer $token" }
Write-Output "TOKEN_OK"

Step "Set invoice settings"
$settingsPayload = @{
  invoice_default_amount = 12000
  personal_without_gst_default_amount = 12000
  payment_upi_id = "aisetu@upi"
  payment_account_name = "AI SETU"
  payment_qr_image_url = "https://example.com/qr.png"
  invoice_seq_with_gst = 1
  invoice_seq_without_gst = 1
  invoice_verifier_roles = "ADMIN"
  invoice_header_bg = "#1f2937"
} | ConvertTo-Json
$settingsRes = Invoke-RestMethod -Uri "$base/billing/settings" -Method Put -Headers $headers -ContentType "application/json" -Body $settingsPayload
Write-Output ("SETTINGS_OK seq_gst=" + $settingsRes.invoice_seq_with_gst + " seq_no_gst=" + $settingsRes.invoice_seq_without_gst)

Step "Workflow options"
$opts = Invoke-RestMethod -Uri "$base/billing/workflow/options" -Method Get -Headers $headers
Write-Output ("OPTIONS_OK can_verify=" + $opts.permissions.can_verify_or_send)

Step "Resolve valid workflow"
$cases = @(
  @{ payment_type="BUSINESS_ACCOUNT"; gst_type="WITH_GST"; amount=$null },
  @{ payment_type="PERSONAL_ACCOUNT"; gst_type="WITH_GST"; amount=15000 },
  @{ payment_type="PERSONAL_ACCOUNT"; gst_type="WITHOUT_GST"; amount=$null },
  @{ payment_type="CASH"; gst_type="WITH_GST"; amount=18000 },
  @{ payment_type="CASH"; gst_type="WITHOUT_GST"; amount=5000 }
)
foreach ($c in $cases) {
  $json = $c | ConvertTo-Json
  $r = Invoke-RestMethod -Uri "$base/billing/workflow/resolve" -Method Post -Headers $headers -ContentType "application/json" -Body $json
  Write-Output ("RESOLVE_OK " + $c.payment_type + "/" + $c.gst_type + " amount=" + $r.amount + " requires_qr=" + $r.requires_qr + " source=" + $r.amount_source)
}

Step "Resolve invalid BUSINESS_ACCOUNT/WITHOUT_GST"
$bad = @{ payment_type="BUSINESS_ACCOUNT"; gst_type="WITHOUT_GST"; amount=12000 } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri "$base/billing/workflow/resolve" -Method Post -Headers $headers -ContentType "application/json" -Body $bad | Out-Null
  Write-Output "INVALID_CASE_UNEXPECTED_SUCCESS"
} catch {
  $code = $_.Exception.Response.StatusCode.value__
  Write-Output ("INVALID_CASE_EXPECTED_ERROR status=" + $code)
}

function New-Invoice([string]$name, [string]$phone, [string]$ptype, [string]$gtype, $amount) {
  $payload = @{
    invoice_client_name = $name
    invoice_client_phone = $phone
    payment_type = $ptype
    gst_type = $gtype
    amount = $amount
    service_description = "LAST PRELIMS"
  } | ConvertTo-Json
  return Invoke-RestMethod -Uri "$base/billing/" -Method Post -Headers $headers -ContentType "application/json" -Body $payload
}

Step "Create invoices for sequence test"
$inv1 = New-Invoice "Client A" "9000000001" "BUSINESS_ACCOUNT" "WITH_GST" 6999
$inv2 = New-Invoice "Client B" "9000000002" "CASH" "WITH_GST" 8000
$inv3 = New-Invoice "Client C" "9000000003" "PERSONAL_ACCOUNT" "WITHOUT_GST" $null
$inv4 = New-Invoice "Client D" "9000000004" "CASH" "WITHOUT_GST" 5000
Write-Output ("INV1 " + $inv1.invoice_number + " | " + $inv1.payment_type + "/" + $inv1.gst_type)
Write-Output ("INV2 " + $inv2.invoice_number + " | " + $inv2.payment_type + "/" + $inv2.gst_type)
Write-Output ("INV3 " + $inv3.invoice_number + " | " + $inv3.payment_type + "/" + $inv3.gst_type + " amount=" + $inv3.amount)
Write-Output ("INV4 " + $inv4.invoice_number + " | " + $inv4.payment_type + "/" + $inv4.gst_type)

Step "Invoice actions"
$act = Invoke-RestMethod -Uri "$base/billing/$($inv1.id)/actions" -Method Get -Headers $headers
Write-Output ("ACTIONS can_verify=" + $act.can_verify + " can_send_whatsapp=" + $act.can_send_whatsapp)

Step "Filter API"
$f1 = Invoke-RestMethod -Uri "$base/billing/?payment_type=CASH&gst_type=WITH_GST&limit=20" -Method Get -Headers $headers
$f2 = Invoke-RestMethod -Uri "$base/billing/?gst_type=WITHOUT_GST&limit=20" -Method Get -Headers $headers
Write-Output ("FILTER_CASH_WITH_GST count=" + @($f1).Count)
Write-Output ("FILTER_WITHOUT_GST count=" + @($f2).Count)

Step "Verify and send"
$v = Invoke-RestMethod -Uri "$base/billing/$($inv1.id)/verify" -Method Patch -Headers $headers
$s = Invoke-RestMethod -Uri "$base/billing/$($inv1.id)/send-whatsapp" -Method Post -Headers $headers
Write-Output ("VERIFY_STATUS=" + $v.invoice_status + " SEND_STATUS=" + $s.invoice_status + " WA_URL=" + [bool]$s.wa_url + " PHONEPE_LINK=" + [bool]$s.phonepe_payment_link)

Step "Invoice HTML checks"
$h1 = Invoke-WebRequest -UseBasicParsing -Uri "$base/billing/$($inv1.id)/invoice-html" -Method Get -Headers $headers
$h3 = Invoke-WebRequest -UseBasicParsing -Uri "$base/billing/$($inv3.id)/invoice-html" -Method Get -Headers $headers
$txt1 = $h1.Content
$txt3 = $h3.Content
Write-Output ("HTML1_HAS_CGST9=" + $txt1.Contains("CGST (9%)"))
Write-Output ("HTML3_HAS_CGST0=" + $txt3.Contains("CGST (0%)"))
Write-Output ("HTML_HAS_WHITE_LOGO=" + $txt1.Contains("/frontend/images/white%20logo.png"))

Step "Done"
Write-Output "WORKFLOW_TEST_COMPLETE"
