Write-Host "Starting Cloudflare Tunnel for ExpenseIQ Web Simulator (port 8000)..."
npx -y cloudflared tunnel --url http://localhost:8000
