# Nginx Configuration for n8n Proxy (Fix 60-Second Timeout)

## Quick Setup

### 1. In Your Nginx Web Interface

Add this to the **Custom Nginx Configuration** field for your **n8n proxy host** (the one that forwards to `n8n.ssl-labs.ai`):

```nginx
# TCP keepalive - CRITICAL to prevent 60-second VPN timeout
# This is the MOST IMPORTANT setting - sends keepalive packets to prevent VPN from dropping idle connections
proxy_socket_keepalive on;

# Increase timeouts for long-running n8n requests (45+ minutes)
proxy_read_timeout 7200s;
proxy_send_timeout 7200s;
send_timeout 7200s;
proxy_connect_timeout 60s;
```

**IMPORTANT:** This minimal config only includes the essential TCP keepalive and timeout settings. It does NOT override any headers or SSL settings, so it won't break your existing proxy configuration.

### 2. Configure VPN Bypass (CRITICAL - Already Done)

The `docker-compose.yaml` has been configured to bypass VPN for your local network (192.168.0.0/24) where n8n is hosted. This prevents the 60-second VPN timeout.

**After updating docker-compose.yaml**, restart containers:
```bash
docker compose down
docker compose up -d
```

### 3. No Code Changes Needed

Your app already connects to `https://n8n.ssl-labs.ai`, which goes through your nginx proxy. The nginx configuration above adds TCP keepalive for additional reliability (though bypassing VPN is the main fix).

### 4. Restart Containers (Required After docker-compose.yaml Changes)

```bash
docker compose down
docker compose up -d
```

This will apply the VPN bypass configuration for your local network.

## What This Fixes

- **60-second timeout**: VPN bypass for local network (192.168.0.0/24) prevents VPN timeout - n8n traffic no longer goes through VPN
- **TCP keepalive**: `proxy_socket_keepalive on;` in nginx provides additional reliability for long connections
- **Long requests**: `7200s` timeouts allow n8n requests that take 45+ minutes

## Troubleshooting

**Can't access n8n at all after adding config?**

1. **Check nginx logs** for syntax errors
2. **Try the minimal config above first** - it only adds TCP keepalive, no SSL/header changes
3. **If you previously had SSL config that broke things**, remove it and use the minimal config above

**Still getting 60-second timeout?**

**SOLUTION: Bypass VPN for local network traffic**

Since n8n doesn't need VPN access and is on your local network (192.168.0.0/24), we've configured gluetun to bypass VPN for all local network traffic.

The `docker-compose.yaml` now includes:
```yaml
- FIREWALL_OUTBOUND_SUBNETS=192.168.0.0/24
```

This means:
- ✅ Traffic to your n8n server (192.168.0.2) bypasses VPN completely
- ✅ Traffic to your nginx proxy (if on local network) also bypasses VPN
- ✅ No more 60-second VPN timeout for n8n requests
- ✅ Other traffic (OpenAI, etc.) still goes through VPN as needed

**After updating docker-compose.yaml:**
1. Restart containers: `docker compose down && docker compose up -d`
2. Test n8n requests - they should no longer timeout at 60 seconds
3. The nginx `proxy_socket_keepalive on;` config is still recommended for additional reliability

**SSL errors?**

The minimal config above doesn't touch SSL settings - it lets nginx proxy manager handle everything. If you get SSL errors, they're likely from your base proxy configuration, not this custom config.

