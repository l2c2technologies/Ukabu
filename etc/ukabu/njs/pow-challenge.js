// ========================================
// UKABU WAF v1.0 - Phase 1
// PoW Challenge Logic (NJS Module)
// Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
// ========================================
//
// Location: /etc/ukabu/njs/pow-challenge.js
//
// This module handles:
//   - Challenge generation with HMAC signing
//   - Solution validation (SHA-256 difficulty check)
//   - Token generation/validation
//   - Socket communication stubs (Phase 2)
//
// ========================================

// Load HMAC secret from file
function loadHmacSecret(r) {
    var secretFile = r.variables.pow_hmac_secret_file;
    
    if (!secretFile || secretFile === "") {
        r.error("No HMAC secret file configured for domain: " + r.variables.host);
        return null;
    }
    
    try {
        // Read secret file
        var fs = require('fs');
        var content = fs.readFileSync(secretFile, 'utf8');
        
        // Parse secret file (format: hmac_secret=value)
        var lines = content.split('\n');
        var secret = null;
        var secretOld = null;
        var rotationExpires = null;
        
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (line.startsWith('hmac_secret=')) {
                secret = line.substring('hmac_secret='.length);
            } else if (line.startsWith('hmac_secret_old=')) {
                secretOld = line.substring('hmac_secret_old='.length);
            } else if (line.startsWith('rotation_expires=')) {
                rotationExpires = line.substring('rotation_expires='.length);
            }
        }
        
        if (!secret) {
            r.error("HMAC secret not found in file: " + secretFile);
            return null;
        }
        
        return {
            secret: secret,
            secretOld: secretOld || null,
            rotationExpires: rotationExpires ? new Date(rotationExpires) : null
        };
    } catch (e) {
        r.error("Failed to read HMAC secret file: " + secretFile + " - " + e.message);
        return null;
    }
}

// Generate PoW Challenge
function generateChallenge(r) {
    try {
        var crypto = require('crypto');
        
        // Get configuration
        var difficulty = parseInt(r.variables.pow_difficulty) || 18;
        var secretData = loadHmacSecret(r);
        
        if (!secretData) {
            r.return(500, JSON.stringify({
                error: "Server configuration error"
            }));
            return;
        }
        
        // Generate challenge: timestamp:random
        var timestamp = Date.now().toString();
        var random = crypto.createHash('sha256')
            .update(Math.random().toString())
            .digest('hex')
            .substring(0, 16);
        
        var challenge = timestamp + ':' + random;
        
        // Sign challenge with HMAC
        var hmac = crypto.createHmac('sha256', secretData.secret)
            .update(challenge)
            .digest('hex');
        
        // Return challenge data
        var data = {
            challenge: challenge,
            hmac: hmac,
            difficulty: difficulty
        };
        
        r.headersOut['Content-Type'] = 'application/json';
        r.return(200, JSON.stringify(data));
        
    } catch (e) {
        r.error("Challenge generation error: " + e.message);
        r.return(500, JSON.stringify({
            error: "Challenge generation failed"
        }));
    }
}

// Validate PoW Solution
function validateSolution(r) {
    try {
        var crypto = require('crypto');
        
        // Parse request body
        var body;
        try {
            body = JSON.parse(r.requestText || r.requestBody);
        } catch (e) {
            r.return(400, JSON.stringify({
                success: false,
                error: "Invalid JSON"
            }));
            return;
        }
        
        // Validate required fields
        if (!body.challenge || body.nonce === undefined || !body.hmac) {
            r.return(400, JSON.stringify({
                success: false,
                error: "Missing required fields"
            }));
            return;
        }
        
        // Load HMAC secret
        var secretData = loadHmacSecret(r);
        if (!secretData) {
            r.return(500, JSON.stringify({
                success: false,
                error: "Server configuration error"
            }));
            return;
        }
        
        // Verify HMAC signature
        var expectedHmac = crypto.createHmac('sha256', secretData.secret)
            .update(body.challenge)
            .digest('hex');
        
        if (body.hmac !== expectedHmac) {
            // Phase 2: Notify daemon of HMAC failure
            // notifyFailure(r, "hmac_failed");
            
            r.return(403, JSON.stringify({
                success: false,
                error: "Invalid challenge signature"
            }));
            return;
        }
        
        // Check challenge timestamp (must be < 5 minutes old)
        var challengeParts = body.challenge.split(':');
        var timestamp = parseInt(challengeParts[0]);
        var now = Date.now();
        var maxAge = 300000; // 5 minutes in milliseconds
        
        if (now - timestamp > maxAge) {
            // Phase 2: Notify daemon of timeout
            // notifyFailure(r, "timeout");
            
            r.return(403, JSON.stringify({
                success: false,
                error: "Challenge expired"
            }));
            return;
        }
        
        // Verify proof of work
        var solution = body.challenge + ':' + body.nonce;
        var hash = crypto.createHash('sha256')
            .update(solution)
            .digest('hex');
        
        var difficulty = parseInt(r.variables.pow_difficulty) || 18;
        
        if (!checkDifficulty(hash, difficulty)) {
            // Phase 2: Notify daemon of invalid solution
            // notifyFailure(r, "invalid_solution");
            
            r.return(403, JSON.stringify({
                success: false,
                error: "Invalid proof of work"
            }));
            return;
        }
        
        // Solution is valid! Generate session token
        var sessionData = now.toString() + ':' + r.variables.remote_addr;
        var sessionToken = crypto.createHmac('sha256', secretData.secret)
            .update(sessionData)
            .digest('hex');
        
        var cookieValue = sessionToken + ':' + now;
        var duration = parseInt(r.variables.pow_cookie_duration) || 604800;
        
        // Set cookie
        r.headersOut['Set-Cookie'] = 
            'pow_token=' + cookieValue + 
            '; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=' + duration;
        
        // Phase 2: Notify daemon of success (reset strikes)
        // notifySuccess(r);
        
        // Get redirect URL from query parameter
        var redirectUrl = r.args.redirect || '/';
        
        r.headersOut['Content-Type'] = 'application/json';
        r.return(200, JSON.stringify({
            success: true,
            redirect: redirectUrl
        }));
        
    } catch (e) {
        r.error("Solution validation error: " + e.message);
        r.return(500, JSON.stringify({
            success: false,
            error: "Validation failed"
        }));
    }
}

// Check if hash meets difficulty requirement
function checkDifficulty(hash, difficulty) {
    var requiredZeros = Math.floor(difficulty / 4);
    var prefix = '0'.repeat(requiredZeros);
    
    if (!hash.startsWith(prefix)) {
        return false;
    }
    
    // Check remaining bits (if difficulty not divisible by 4)
    var remainingBits = difficulty % 4;
    if (remainingBits > 0) {
        var nextChar = parseInt(hash.charAt(requiredZeros), 16);
        var mask = (1 << (4 - remainingBits)) - 1;
        return (nextChar & ~mask) === 0;
    }
    
    return true;
}

// Validate Token (called via js_var)
function validateToken(r) {
    try {
        var cookie = r.headersIn.Cookie;
        
        if (!cookie || cookie.indexOf('pow_token=') === -1) {
            return "0";
        }
        
        // Extract token from cookie
        var match = cookie.match(/pow_token=([^;]+)/);
        if (!match) {
            return "0";
        }
        
        var parts = match[1].split(':');
        if (parts.length !== 2) {
            return "0";
        }
        
        var token = parts[0];
        var timestamp = parseInt(parts[1]);
        
        // Check if expired
        var now = Date.now();
        var duration = parseInt(r.variables.pow_cookie_duration) || 604800;
        var maxAge = duration * 1000; // Convert to milliseconds
        
        if (now - timestamp > maxAge) {
            return "0";
        }
        
        // Load HMAC secret
        var secretData = loadHmacSecret(r);
        if (!secretData) {
            return "0";
        }
        
        // Verify token signature (try current secret)
        var crypto = require('crypto');
        var expectedToken = crypto.createHmac('sha256', secretData.secret)
            .update(timestamp.toString() + ':' + r.variables.remote_addr)
            .digest('hex');
        
        if (token === expectedToken) {
            return "1";
        }
        
        // If secret rotation in progress, try old secret
        if (secretData.secretOld && secretData.rotationExpires) {
            if (now < secretData.rotationExpires.getTime()) {
                var expectedTokenOld = crypto.createHmac('sha256', secretData.secretOld)
                    .update(timestamp.toString() + ':' + r.variables.remote_addr)
                    .digest('hex');
                
                if (token === expectedTokenOld) {
                    return "1";
                }
            }
        }
        
        return "0";
        
    } catch (e) {
        r.error("Token validation error: " + e.message);
        return "0";
    }
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Phase 2 Stubs: Daemon Communication
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// These functions will communicate with ukabu-trackerd via Unix socket
// Phase 1: Just log to nginx error log
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function notifyFailure(r, reason) {
    // Phase 1: Log failure
    r.warn("PoW failure - IP: " + r.variables.remote_addr + 
           " Domain: " + r.variables.host + 
           " Reason: " + reason);
    
    // Phase 2: Send to daemon via Unix socket
    // var message = {
    //     type: "failure",
    //     ip: r.variables.remote_addr,
    //     domain: r.variables.host,
    //     reason: reason,
    //     timestamp: new Date().toISOString()
    // };
    // sendToDaemon(r, message);
}

function notifySuccess(r) {
    // Phase 1: Log success
    r.log("PoW success - IP: " + r.variables.remote_addr + 
          " Domain: " + r.variables.host);
    
    // Phase 2: Send to daemon via Unix socket
    // var message = {
    //     type: "success",
    //     ip: r.variables.remote_addr,
    //     domain: r.variables.host,
    //     timestamp: new Date().toISOString()
    // };
    // sendToDaemon(r, message);
}

function sendToDaemon(r, message) {
    // Phase 2: Implementation
    // try {
    //     var sock = require('unix_socket');
    //     var conn = sock.connect('/var/run/ukabu/tracker.sock');
    //     conn.write(JSON.stringify(message) + '\n');
    //     var response = conn.read();
    //     conn.close();
    //     return JSON.parse(response);
    // } catch (e) {
    //     r.error("Failed to contact daemon: " + e.message);
    //     return null;
    // }
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Export Functions
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default { 
    generateChallenge, 
    validateSolution, 
    validateToken 
};
