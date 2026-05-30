# Oracle Cloud Free Tier backend deployment

This folder contains a VM bootstrap path for deploying the FastAPI backend on an Oracle Cloud Always Free compute instance.

## Expected VM

- Ubuntu 22.04 or 24.04
- Public IP assigned
- Ingress open for TCP `22`, `80`, and optionally `443`
- Outbound internet access

Oracle security list / network security group rules must allow HTTP traffic on port `80`. The script also enables the OS firewall for `OpenSSH` and `Nginx Full`.

## Deploy

SSH into the VM, then run:

```bash
curl -fsSL https://raw.githubusercontent.com/KeshavKhippal/Veersa-Victors/main/medauth-sentinel/deploy/oracle/bootstrap-backend.sh -o bootstrap-backend.sh
chmod +x bootstrap-backend.sh
sudo GROQ_API_KEY="your_groq_api_key" TAVILY_API_KEY="your_tavily_api_key" ./bootstrap-backend.sh
```

After the script finishes, verify:

```bash
curl http://YOUR_VM_PUBLIC_IP/api/health
sudo systemctl status medauth-backend --no-pager
```

Use `http://YOUR_VM_PUBLIC_IP` as the backend base URL for Vercel's `PUBLIC_API_URL`.

## Updating after a GitHub push

```bash
sudo /opt/medauth-sentinel/repo/medauth-sentinel/deploy/oracle/redeploy-backend.sh
```
