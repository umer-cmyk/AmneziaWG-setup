const express = require('express');
const { exec } = require('child_process');
const app = express();
const PORT = 9008;

app.use(express.json());

// Path to your script
const SCRIPT_PATH = "/etc/amnezia/amneziawg/scripts/add_peer.sh";
// Path to the lock file (Linux will create this if it doesn't exist)
const LOCK_FILE = "/var/lock/amnezia_peer_alloc.lock";

app.post('/api/register-key-get-ip', (req, res) => {
    const { public_key } = req.body;

    // --- CHANGE IS HERE ---
    // sudo flock <lockfile> <command>
    // This forces the OS to run the script one at a time.
    const command = `sudo flock ${LOCK_FILE} ${SCRIPT_PATH} "${public_key}"`;

    exec(command, (error, stdout) => {
        if (error) {
            console.error(`Exec Error: ${error.message}`);
            // If the script failed (or timed out), return error
            return res.status(500).json({ error: "Failed to add peer" });
        }

        const allocatedIp = stdout.trim();
        
        return res.status(200).json({
            ipaddress: allocatedIp
        });
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`VPN API running on port ${PORT}`);
});