const express = require('express');
const { exec } = require('child_process');
const app = express();
const PORT = 9008;

app.use(express.json());

// Path to your script
const SCRIPT_PATH = "/etc/amnezia/amneziawg/scripts/add_peer.sh";

// 1. API Endpoint to register public key and get allocated IP
app.post('/api/register-key-get-ip', (req, res) => {
    const { public_key } = req.body;

    // 2. Execute Script using sudo
    const command = `sudo ${SCRIPT_PATH} "${public_key}"`;

    exec(command, (error, stdout) => {
        if (error) {
            console.error(`Exec Error: ${error.message}`);
            return res.status(500).json({ error: "Failed to add peer" });
        }

        // 3. Success
        const allocatedIp = stdout.trim();
        
        return res.status(200).json({
            ipaddress: allocatedIp
        });
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`VPN API running on port ${PORT}`);
});