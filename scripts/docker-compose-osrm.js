#!/usr/bin/env node
/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

/**
 * Wrapper script to run docker-compose with the correct OSRM image for the current architecture
 *
 * Usage:
 *   node scripts/docker-compose-osrm.js [docker-compose args...]
 *
 * Examples:
 *   node scripts/docker-compose-osrm.js up -d
 *   node scripts/docker-compose-osrm.js down
 *   node scripts/docker-compose-osrm.js ps
 */

const { spawnSync } = require('child_process');
const os = require('os');
const path = require('path');

// Architecture to Docker image mapping
const OSRM_IMAGES = {
    x64: 'ghcr.io/project-osrm/osrm-backend:v6.0.0@sha256:5116c66d814485be70bc7b239be890e4d36f62b1025a2f1c8139c20fa2697309',
    arm64: 'ghcr.io/project-osrm/osrm-backend:v6.0.0@sha256:733da1be48587358a417750655cc4748bbae9af60e3ace610db68d4febe038d8'
};

// Get the correct image for this architecture
const arch = os.arch();
const osrmImage = OSRM_IMAGES[arch];

if (!osrmImage) {
    console.error(`[ERROR] Unsupported architecture: ${arch}`);
    console.error('[ERROR] Supported architectures: x64 (amd64), arm64');
    console.error('[ERROR] Cannot determine correct OSRM v6.0.0 image for your system.');
    process.exit(1);
}

console.log(`[INFO] Detected architecture: ${arch}`);
console.log(`[INFO] Using OSRM image: ${osrmImage}`);
console.log('');

// Get docker-compose arguments from command line
const args = process.argv.slice(2);

// Set environment variable and run docker-compose
const env = {
    ...process.env,
    OSRM_IMAGE: osrmImage
};

// Run docker-compose with the environment variable set
const result = spawnSync('docker-compose', args, {
    stdio: 'inherit',
    env: env,
    shell: true
});

// Exit with the same code as docker-compose
process.exit(result.status || 0);
