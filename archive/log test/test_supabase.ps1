$headers = @{
  "apikey" = "sb_publishable_rTX40L76La_B_fCovEREnA_7cVV0KaS"
  "Authorization" = "Bearer sb_publishable_rTX40L76La_B_fCovEREnA_7cVV0KaS"
  "Content-Type" = "application/json"
}

$body = @{
  entry_text = "test kirje API kaudu"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "https://pfptxlcwilqlavnfcjje.supabase.co/rest/v1/rpc/add_log_entry" `
  -Method Post `
  -Headers $headers `
  -Body $body