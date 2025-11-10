# UKABU WAF Component A (ukabu-core) - Testing Guide

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

---

## Prerequisites

Before testing, ensure:

âœ… nginx with njs module installed  
âœ… UKABU files copied to /etc/ukabu/  
âœ… HMAC secrets generated and configured  
âœ… domains.json configured with your domain  
âœ… nginx.conf includes config.conf in http{} block  
âœ… Vhost includes endpoints.inc and enforcement.inc  
âœ… nginx configuration tested: `sudo nginx -t`  
âœ… nginx reloaded: `sudo systemctl reload nginx`  

---

## Test Suite

### Test 1: Basic Challenge Flow (Browser)

**Objective:** Verify end-to-end PoW challenge works

**Steps:**
1. Open browser (Firefox/Chrome)
2. Navigate to: `https://example.com/`
3. **Expected:** Redirect to `/ukabu_verify?redirect=/`
4. **Expected:** See challenge page with progress bar
5. **Expected:** Mining starts (difficulty shown)
6. **Wait:** ~15-30 seconds (difficulty 18)
7. **Expected:** "Verified!" message appears
8. **Expected:** Automatic redirect to `/`
9. **Expected:** Cookie `pow_token` is set (check DevTools)
10. **Expected:** Subsequent requests bypass challenge

**Verification:**
```bash
# Check nginx access log
sudo tail -f /var/log/nginx/access.log | grep ukabu_combined

# Should see:
# X-Ukabu-Status: 200 (challenge issued)
# X-Ukabu-Status: 103 (valid token on subsequent requests)
```

**Success Criteria:** âœ… Challenge completes, token issued, access granted

---

### Test 2: Path Whitelist (Static Assets)

**Objective:** Verify static assets bypass PoW

**Test:**
```bash
curl -I https://example.com/static/style.css
```

**Expected Response:**
```
HTTP/2 200 
x-ukabu-status: 100
x-ukabu-decision: path_whitelisted
```

**Verification:**
```bash
# Check that no redirect occurred
# Check X-Ukabu-Status header
curl -I https://example.com/images/logo.png | grep -i ukabu
```

**Success Criteria:** âœ… 200 OK, Status: 100, No challenge redirect

---

### Test 3: IP Whitelist

**Objective:** Verify whitelisted IPs bypass PoW

**Setup:**
1. Add your IP to `/etc/ukabu/config/ip_whitelist.conf`
2. Reload nginx: `sudo systemctl reload nginx`

**Test:**
```bash
curl -I https://example.com/
```

**Expected Response:**
```
HTTP/2 200 
x-ukabu-status: 101
x-ukabu-decision: ip_whitelisted
```

**Success Criteria:** âœ… Direct access without challenge, Status: 101

---

### Test 4: Path Blacklist

**Objective:** Verify blacklisted paths are blocked

**Test:**
```bash
curl -I https://example.com/wp-admin/
```

**Expected Response:**
```
(connection closed by server - 444)
x-ukabu-status: 002
x-ukabu-decision: path_blacklisted
```

**Note:** curl may show "Empty reply from server" (this is correct for 444)

**Success Criteria:** âœ… Connection closed, Status: 002

---

### Test 5: Non-Browser Client

**Objective:** Verify non-browser clients are blocked

**Test:**
```bash
# curl without browser User-Agent
curl -I https://example.com/
```

**Expected Response:**
```
HTTP/2 406 
x-ukabu-status: 201
x-ukabu-decision: non_browser_blocked
```

**Test with fake browser UA:**
```bash
curl -I -H "User-Agent: Mozilla/5.0" https://example.com/
```

**Expected Response:**
```
HTTP/2 302 
location: /ukabu_verify?redirect=/
x-ukabu-status: 200
x-ukabu-decision: challenge_issued
```

**Success Criteria:** âœ… Plain curl blocked (406), Fake browser redirected (302)

---

### Test 6: Challenge Endpoints

**Test 6a: Generate Challenge**
```bash
curl https://example.com/ukabu_challenge
```

**Expected Response:**
```json
{
  "challenge": "1731153045000:a1b2c3d4e5f6g7h8",
  "hmac": "9876543210fedcba...",
  "difficulty": 18
}
```

**Test 6b: Validate Solution (Invalid)**
```bash
curl -X POST https://example.com/ukabu_validate \
  -H "Content-Type: application/json" \
  -d '{
    "challenge": "1731153045000:a1b2c3d4",
    "hmac": "invalid",
    "nonce": 12345
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "error": "Invalid challenge signature"
}
```

**Success Criteria:** âœ… Endpoints respond correctly, validation works

---

### Test 7: Token Validation

**Objective:** Verify token expiration and validation

**Test 7a: With Valid Token**
1. Complete PoW challenge in browser
2. Extract token cookie from DevTools
3. Test with curl:
```bash
curl -I https://example.com/ \
  -H "Cookie: pow_token=TOKEN_HERE"
```

**Expected:** 200 OK, X-Ukabu-Status: 103

**Test 7b: With Expired Token**
1. Wait for token to expire (default: 7 days - impractical)
2. Or manually set short duration in domains.json:
```json
"cookie_duration": 60  // 60 seconds
```
3. Wait 61 seconds
4. Request with old token

**Expected:** 302 redirect to challenge (token expired)

**Test 7c: With Invalid Token**
```bash
curl -I https://example.com/ \
  -H "Cookie: pow_token=invalid_token:1234567890"
```

**Expected:** 302 redirect to challenge

**Success Criteria:** âœ… Valid tokens accepted, invalid/expired rejected

---

### Test 8: No-JavaScript Page

**Objective:** Verify no-JS users see help page

**Steps:**
1. Open browser
2. Disable JavaScript (or use NoScript extension)
3. Navigate to: `https://example.com/`
4. **Expected:** Redirect to `/ukabu_verify`
5. **Expected:** Noscript meta tag redirects to `/ukabu_help`
6. **Expected:** See browser-specific help page

**Or test with curl:**
```bash
curl https://example.com/ukabu_help
```

**Expected:** HTML page with instructions to enable JavaScript

**Success Criteria:** âœ… No-JS users see helpful error page

---

### Test 9: Difficulty Levels

**Objective:** Verify different difficulty settings work

**Setup:**
Edit `/etc/ukabu/config/domains.json`:
```json
"example.com": {
  "pow_difficulty": 12  // ~1-2 seconds (easy)
}
```

**Test:**
1. Reload nginx
2. Complete challenge in browser
3. **Expected:** Faster solving time (~1-2 seconds)

**Try different difficulties:**
- 12 bits = ~1-2s (testing)
- 16 bits = ~5-10s (light)
- 18 bits = ~15-30s (default)
- 20 bits = ~1-2min (heavy)

**Success Criteria:** âœ… Difficulty changes affect solving time

---

### Test 10: Multiple Domains

**Objective:** Verify per-domain configuration works

**Setup:**
Add second domain to domains.json:
```json
"test.example.com": {
  "pow_difficulty": 16,
  "hmac_secret_file": "/etc/ukabu/secrets/test.example.com.key",
  "exempt_paths": ["/api/*"]
}
```

**Test:**
1. Access `https://test.example.com/`
2. **Expected:** Challenge with difficulty 16
3. Access `https://test.example.com/api/endpoint`
4. **Expected:** Bypass (path whitelisted)

**Success Criteria:** âœ… Different domains use different settings

---

## Troubleshooting

### Challenge Page Not Loading

**Symptoms:** Blank page or 404 on /ukabu_verify

**Checks:**
```bash
# Verify endpoints.inc is included
sudo nginx -T | grep "include.*endpoints.inc"

# Verify challenge.html exists
ls -la /etc/ukabu/pages/challenge.html

# Check nginx error log
sudo tail -f /var/log/nginx/error.log
```

**Fix:** Ensure endpoints.inc is included in server{} block

---

### Token Not Being Set

**Symptoms:** Challenge completes but redirects to challenge again

**Checks:**
```bash
# Check HMAC secret file exists and is readable
sudo ls -la /etc/ukabu/secrets/

# Check secret file format
sudo cat /etc/ukabu/secrets/example.com.key

# Check nginx can read NJS module
sudo nginx -T | grep "js_import pow"

# Check browser console for errors
# (DevTools â†’ Console)
```

**Fix:** 
- Ensure secret file has correct format
- Ensure nginx can read secret file (permissions)
- Check NJS module is loaded

---

### "Server configuration error"

**Symptoms:** Challenge generation fails with 500 error

**Checks:**
```bash
# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Look for messages like:
# "No HMAC secret file configured"
# "Failed to read HMAC secret file"
```

**Fix:**
- Verify domains.json has correct hmac_secret_file path
- Verify secret file exists and is readable
- Reload nginx after fixing

---

### Challenge Solving Too Slow

**Symptoms:** Takes >1 minute to solve

**Checks:**
```bash
# Check configured difficulty
grep pow_difficulty /etc/ukabu/config/domains.json
```

**Fix:** Lower difficulty for testing:
```json
"pow_difficulty": 12  // Fast for testing
```

Then reload nginx

---

### Path Whitelist Not Working

**Symptoms:** Static assets require challenge

**Checks:**
```bash
# Test specific path
curl -I https://example.com/static/test.css | grep ukabu

# Check path_whitelist.conf
cat /etc/ukabu/config/path_whitelist.conf

# Check nginx map
sudo nginx -T | grep -A 20 "map.*is_path_whitelisted"
```

**Fix:**
- Ensure path matches pattern in config
- Remember: Use prefix match (~^/static/)
- Reload nginx after changes

---

## Performance Testing

### Load Test with ApacheBench

**Without UKABU (direct to upstream):**
```bash
ab -n 1000 -c 10 http://localhost:8080/
```

**With UKABU (with valid token):**
```bash
# First get token by completing challenge in browser
# Extract cookie value
ab -n 1000 -c 10 -C "pow_token=YOUR_TOKEN_HERE" https://example.com/
```

**Expected:** Minimal performance impact with valid token (<5ms overhead)

---

### Monitor nginx Performance

```bash
# Watch request rates
sudo tail -f /var/log/nginx/access.log | pv -l -i 1 > /dev/null

# Check nginx worker processes
ps aux | grep nginx

# Monitor CPU/memory
top -p $(pgrep -d',' nginx)
```

---

## Success Checklist

After completing all tests, verify:

- [ ] Challenge page loads correctly
- [ ] Challenge solves and issues token
- [ ] Token persists across requests
- [ ] Static assets bypass challenge (Status: 100)
- [ ] Whitelisted IPs bypass challenge (Status: 101)
- [ ] Blacklisted paths are blocked (Status: 002)
- [ ] Non-browsers are blocked (Status: 201)
- [ ] No-JS users see help page
- [ ] Different difficulty levels work
- [ ] Multiple domains work independently
- [ ] Performance is acceptable

---

## Component A (ukabu-core) Limitations

Remember, Component A (ukabu-core) does NOT include:

âŒ **Strike tracking** - No automatic blocking after failures  
âŒ **ipset integration** - No firewall-level blocking  
âŒ **Search engine detection** - Googlebot/Bingbot not exempted  
âŒ **XFF handling** - CDN/proxy IPs not handled  
âŒ **Daemon** - No background service  
âŒ **CLI tools** - No automated configuration  

These features come in later phases.

---

## Next Steps

Once Component A (ukabu-core) is tested and working:

1. **Component B (ukabu-monitor):** Add Go daemon for strike tracking and ipset blocking
2. **Component C (ukabu-manager):** Add Python CLI for configuration management
3. **Component D (ukabu-extras):** Add search engine detection, XFF handling, ML extraction
4. **Phase 5:** Add monitoring, Prometheus exporter, documentation

---

**Questions or Issues?**

- Email: indradg@l2c2.co.in
- Organization: L2C2 Technologies

---

**UKABU WAF** - Collaborative Anti-AI Scraper Bot Web Application Firewall
