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
 * Cross-platform OSRM data preparation script
 * Downloads and preprocesses Montreal OSM data for OSRM routing
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const os = require('os');

// Always use project root (parent of scripts directory)
const PROJECT_ROOT = path.join(__dirname, '..');
const DATA_DIR = path.join(PROJECT_ROOT, 'osrm-data');
const OSM_FILE = 'montreal.osm.pbf';
const OSRM_FILE = 'montreal.osrm';
const DOWNLOAD_URL = 'https://download.bbbike.org/osm/bbbike/Montreal/Montreal.osm.pbf';

const skipDownload = process.argv.includes('--skip-download');
const force = process.argv.includes('--force');

// Architecture to Docker image mapping
const OSRM_IMAGES = {
    x64: 'ghcr.io/project-osrm/osrm-backend:v6.0.0@sha256:5116c66d814485be70bc7b239be890e4d36f62b1025a2f1c8139c20fa2697309',
    arm64: 'ghcr.io/project-osrm/osrm-backend:v6.0.0@sha256:733da1be48587358a417750655cc4748bbae9af60e3ace610db68d4febe038d8'
};

// Detect the correct OSRM image for this architecture
function getOSRMImage() {
    const arch = os.arch();
    const image = OSRM_IMAGES[arch];

    if (!image) {
        console.error(`[ERROR] Unsupported architecture: ${arch}`);
        console.error('[ERROR] Supported architectures: x64 (amd64), arm64');
        process.exit(1);
    }

    return image;
}

const OSRM_IMAGE = getOSRMImage();

function log(message) {
    console.log(`[${new Date().toLocaleTimeString()}] ${message}`);
}

function runDocker(args) {
    return new Promise((resolve, reject) => {
        log(`Running: docker ${args.join(' ')}`);
        const child = spawn('docker', args, { stdio: 'inherit' });

        child.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`Docker command failed with exit code ${code}`));
            }
        });

        child.on('error', (err) => {
            reject(err);
        });
    });
}

function downloadFile(url, destPath) {
    return new Promise((resolve, reject) => {
        log(`Downloading from ${url}`);
        log('This may take a few minutes...');

        const file = fs.createWriteStream(destPath);
        const client = url.startsWith('https') ? https : http;

        client.get(url, (response) => {
            if (response.statusCode === 302 || response.statusCode === 301) {
                // Handle redirect
                file.close();
                fs.unlinkSync(destPath);
                downloadFile(response.headers.location, destPath).then(resolve).catch(reject);
                return;
            }

            if (response.statusCode !== 200) {
                file.close();
                fs.unlinkSync(destPath);
                reject(new Error(`Failed to download: HTTP ${response.statusCode}`));
                return;
            }

            const totalBytes = parseInt(response.headers['content-length'], 10);
            let downloadedBytes = 0;
            let lastProgress = 0;

            response.on('data', (chunk) => {
                downloadedBytes += chunk.length;
                const progress = Math.floor((downloadedBytes / totalBytes) * 100);
                if (progress - lastProgress >= 10) {
                    log(`Downloaded: ${progress}% (${Math.floor(downloadedBytes / 1024 / 1024)}MB)`);
                    lastProgress = progress;
                }
            });

            response.pipe(file);

            file.on('finish', () => {
                file.close();
                log('Download complete ✓');
                resolve();
            });
        }).on('error', (err) => {
            file.close();
            fs.unlinkSync(destPath);
            reject(err);
        });
    });
}

async function checkDocker() {
    try {
        await runDocker(['--version']);
        log('Docker is installed ✓');
        return true;
    } catch (error) {
        console.error('[ERROR] Docker is not installed or not running.');
        console.error('[ERROR] Please install Docker Desktop from https://www.docker.com/products/docker-desktop');
        return false;
    }
}

async function main() {
    console.log('==========================================');
    console.log('OSRM Data Preparation for VeloSim');
    console.log('==========================================');
    console.log('');
    console.log(`Project root: ${PROJECT_ROOT}`);
    console.log(`Data directory: ${DATA_DIR}`);
    console.log(`Architecture: ${os.arch()}`);
    console.log(`OSRM Image: ${OSRM_IMAGE}`);
    console.log('');

    // Check Docker
    if (!await checkDocker()) {
        process.exit(1);
    }

    // Create data directory
    if (!fs.existsSync(DATA_DIR)) {
        fs.mkdirSync(DATA_DIR, { recursive: true });
    }

    const osmPath = path.join(DATA_DIR, OSM_FILE);
    const osrmPath = path.join(DATA_DIR, OSRM_FILE);
    // Check for a file that's actually created by the process (fileIndex is created by osrm-extract)
    const osrmFileIndex = path.join(DATA_DIR, `${OSRM_FILE}.fileIndex`);

    // Check if already processed
    if (!force && fs.existsSync(osrmFileIndex)) {
        log('OSRM data already exists!');
        log(`Location: ${DATA_DIR}/`);
        log('Use --force to re-process');
        console.log('');
        console.log('OSRM data is ready to use ✓');
        return;
    }

    // Step 1: Download OSM data
    if (!skipDownload) {
        if (fs.existsSync(osmPath) && !force) {
            log(`OSM file already exists: ${osmPath}`);
        } else {
            if (fs.existsSync(osmPath)) {
                fs.unlinkSync(osmPath);
            }
            await downloadFile(DOWNLOAD_URL, osmPath);
        }
    } else if (!fs.existsSync(osmPath)) {
        console.error('[ERROR] --skip-download specified but OSM file does not exist');
        process.exit(1);
    }

    // Step 2: Extract road network
    log('Extracting road network (car profile)...');
    log('This will take 1-3 minutes...');
    await runDocker([
        'run', '-t', '--rm',
        '-v', `${DATA_DIR}:/data`,
        OSRM_IMAGE,
        'osrm-extract',
        '-p', '/opt/car.lua',
        `/data/${OSM_FILE}`
    ]);
    log('Extraction complete ✓');

    // Step 3: Partition
    log('Preprocessing with MLD algorithm...');
    log('Step 3a: Partitioning...');
    await runDocker([
        'run', '-t', '--rm',
        '-v', `${DATA_DIR}:/data`,
        OSRM_IMAGE,
        'osrm-partition',
        `/data/${OSRM_FILE}`
    ]);
    log('Partitioning complete ✓');

    // Step 4: Customize
    log('Step 3b: Customizing...');
    await runDocker([
        'run', '-t', '--rm',
        '-v', `${DATA_DIR}:/data`,
        OSRM_IMAGE,
        'osrm-customize',
        `/data/${OSRM_FILE}`
    ]);
    log('Customization complete ✓');

    console.log('');
    console.log('==========================================');
    console.log('Data preparation complete!');
    console.log('==========================================');
    console.log('');
    console.log(`Data location: ${DATA_DIR}/`);
    console.log('');
    console.log('Next steps:');
    console.log('  npm run dev    - Start development environment');
    console.log('');
}

main().catch((error) => {
    console.error('[ERROR]', error.message);
    process.exit(1);
});
